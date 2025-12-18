from django.db.models import Value, CharField, Count
import re
from django.db.models import F,Q, Count

from . models import (IndividualEvent,
                      GroupEvent,
                      IndividualEventParticipation,
                      GroupEventParticipation,
                      KalamelaExcludeMembers)

from auth_app.models import (UnitMembers)

from datetime import date

def list_all_individual_events(request):
    district_id = request.user.clergy_district.id
    seniority_category = ['NA', 'Junior', 'Senior']
    
    # Annotate with the count of participants and remaining slots
    individual_events = IndividualEvent.objects.all().order_by('name').annotate(
        already_registered_individual_events_count=Count(
            'individualeventparticipation',  # This refers to the ForeignKey reverse relation
            filter=Q(individualeventparticipation__added_by__clergy_district_id=district_id,
                     individualeventparticipation__seniority_category__in=seniority_category
                     )
        )
    ).annotate(
        remaining_slots=2 - F('already_registered_individual_events_count')
    ).order_by('category','name')
    
    individual_event_dict = {}
    
    for individual_event in individual_events:
        category = individual_event.category
        
        if category not in individual_event_dict:
            individual_event_dict[category]=[]
        
        individual_event_dict[category].append(
            {
                'individual_event':individual_event
            }
        )
    return individual_event_dict


def list_all_group_events(request):
    district_id = request.user.clergy_district.id
    group_events = GroupEvent.objects.all().order_by('name')
    
    group_events_dict={}
    count=None
    for group_event in group_events:
        added_group_events = GroupEventParticipation.objects.filter(
            group_event=group_event,
            added_by=request.user,
            )
        
        added_group_events_ids = added_group_events.values_list(
                                    'group_event_id',
                                    flat=True).distinct()
        
        print("added_group_events_ids",len(added_group_events_ids))
        
        added_group_events_count = added_group_events.values_list(
                                    'participant__registered_user__unit_name_id',
                                    flat=True).distinct()

        group_events_dict[group_event] = []
        if group_event.id in added_group_events_ids:
            group_events_dict[group_event].append(
                {
                    'id': group_event.id, 
                    'name': group_event.name, 
                    'count': len(added_group_events_count) 
                }) 
        else: 
            group_events_dict[group_event].append(
                { 'id': group_event.id, 
                    'name': group_event.name, 
                    'count': 0 } )

    return group_events_dict


def individual_event_members_data(request,event_obj, unit_id = None):
    """
    Custom function to create individual participants data based on the event.
    """
    
    exclude_members_list = KalamelaExcludeMembers.objects.all(
                            ).values_list('members_id', flat=True)
    
     # Query for unit members within the user's clergy district
    already_registered_members = IndividualEventParticipation.objects.filter(
        individual_event=event_obj,
        added_by__clergy_district_id=request.user.clergy_district.id
    ).values_list('participant_id',
                  flat=True)
    
    if unit_id:
        unit_members = UnitMembers.objects.filter(
        registered_user__unit_name__clergy_district_id=request.user.clergy_district.id,
        registered_user__unit_name_id=unit_id,
        ).exclude(id__in=already_registered_members
                  ).exclude(id__in=exclude_members_list)
        
    else:
        unit_members = UnitMembers.objects.filter(
        registered_user__unit_name__clergy_district_id=request.user.clergy_district.id
        ).exclude(id__in=already_registered_members
                  ).exclude(id__in=exclude_members_list)
    

    event_name = event_obj.name
    event_gender=None
    event_seniority_date_range = None
    event_seniority = 'NA'

    # Determine gender based on event name
    if 'boys' in event_name.lower():
        event_gender = 'Male'
    elif 'girls' in event_name.lower():
        event_gender = 'Female'
    
    # Filter members by gender if applicable
    if event_gender:
        unit_members = unit_members.filter(gender=event_gender[:1])
        print("After gender filter:", unit_members.count())

    if 'junior' in event_name.lower():
        event_seniority_date_range = (date(2004, 1, 12),
                                      date(2010, 6, 30))  # Junior age range
        event_seniority = "Junior"

    elif 'senior' in event_name.lower():
        event_seniority_date_range = (date(1989, 7, 1),
                                      date(2004, 1, 11))  # Senior age range
        event_seniority = 'Senior'
    
    if event_seniority_date_range:
        unit_members = unit_members.filter(dob__range=event_seniority_date_range)
        print(f"After seniority filter (DOB range):", unit_members.count())

    unit_members = unit_members.annotate(
        event_seniority=Value(event_seniority, output_field=CharField()),
        event_gender=Value(event_gender, output_field=CharField())
    )

    return unit_members


def add_individual_participant_to_event(event_obj, unit_member_obj, request, seniority_category):
    district_id = request.user.clergy_district.id

    district_participation = IndividualEventParticipation.objects.filter(
                                    individual_event_id=event_obj.id,
                                    added_by__clergy_district_id=district_id
                                    )
    district_participation_count=district_participation.filter(
                                    seniority_category=seniority_category)

    if district_participation_count.count() >= 2:
        message = "This district already has two participants for this event."
        data_saved = False
        return message, data_saved
    
    registered_individual_events = IndividualEventParticipation.objects.all()

    individual_event_by_district = IndividualEventParticipation.objects.filter(
                                added_by=request.user
                                )
    
    individual_event_participants_existing = registered_individual_events.filter(
                                participant=unit_member_obj.id)
    
    individual_event_participants_existing_group = individual_event_by_district.filter(
                                participant=unit_member_obj.id)
    
    participant_event_count = individual_event_participants_existing_group.filter(
                                participant=unit_member_obj.id).count()

    if participant_event_count >= 5:
        message = "This participant is already registered for five individual events."
        data_saved = False
        return message, data_saved
    
    if district_participation.filter(participant=unit_member_obj).exists():
        message = "This participant is already registered for this event."
        data_saved = False
        return message, data_saved

    try:
        event_seniority_junior = (date(2004, 1, 12),
                                    date(2010, 6, 30))  # Junior age range
        event_seniority_senior = (date(1989, 7, 1),
                                    date(2004, 1, 11))  # Senior age range
        
        if event_seniority_junior[0] <= unit_member_obj.dob <= event_seniority_junior[1]:
            chest_number = 100
        elif event_seniority_senior[0] <= unit_member_obj.dob <= event_seniority_senior[1]:
            chest_number = 200
            
        if not registered_individual_events.exists():
            if unit_member_obj.dob in event_seniority_junior:
                chest_number = 100
            elif unit_member_obj.dob in event_seniority_senior:
                chest_number = 200
        else:
            if registered_individual_events.filter(participant_id=unit_member_obj.id).exists():
                chest_number = registered_individual_events.filter(
                                    participant_id=unit_member_obj.id
                                    ).first().chest_number
            else:
                chest_number = registered_individual_events.order_by(
                                '-chest_number'
                                ).first().chest_number
                chest_number = int(chest_number)+1
        
        print("chest_number",chest_number)  
            
        participation = IndividualEventParticipation.objects.create(
                        individual_event=event_obj,
                        participant=unit_member_obj,
                        seniority_category=seniority_category,  # Modify based on your logic
                        chest_number=chest_number,
                        added_by=request.user
                    )
        message = "Participant successfully added to the event."
        data_saved = True
        return message, data_saved

    except Exception as e:
        print("Exception:", str(e))
        message = "Plesae try again"
        data_saved = False
        return message, data_saved


def remove_individual_event_participant_from_event(request, event_id, participant_id):
    try:
        individual_event_participant = IndividualEventParticipation.objects.filter(
            individual_event_id=event_id,
            participant_id=participant_id
        ).first()

        individual_event_participant.delete()
        
        return True

    except Exception:
        return False
    

def group_event_members_data(request, event_obj, unit_id=None):
    """
    Custom function to create individual participants data based on the event.
    """
    
    exclude_members_list = KalamelaExcludeMembers.objects.all(
                            ).values_list('members_id', flat=True)
    
    # Query for unit members within the user's clergy district
    already_registered_members = GroupEventParticipation.objects.filter(
        group_event=event_obj,
        added_by__clergy_district_id=request.user.clergy_district.id
    ).values_list('participant_id',
                  flat=True)
    
    if unit_id:
        unit_members = UnitMembers.objects.filter(
        registered_user__unit_name__clergy_district_id=request.user.clergy_district.id,
        registered_user__unit_name_id=unit_id,
        ).exclude(id__in=already_registered_members
                  ).exclude(id__in=exclude_members_list)
        
    else:
        unit_members = UnitMembers.objects.filter(
        registered_user__unit_name__clergy_district_id=request.user.clergy_district.id
        ).exclude(id__in=already_registered_members
                  ).exclude(id__in=exclude_members_list)
    
    return unit_members


def add_group_participant_to_event(group_event_obj, unit_id, unit_member_objs, request):
    district_id = request.user.clergy_district.id
    
    unique_group_event_ids = GroupEventParticipation.objects.filter(
                                group_event=group_event_obj,
                                )

    unique_group_event_by_dist =  unique_group_event_ids.filter(
                                added_by=request.user
                                )
    
    unique_group_event_by_dist_and_unit = unique_group_event_by_dist.filter(
                                    participant__registered_user__unit_name_id=unit_id
                                ).count()

    already_joined_members =  unique_group_event_ids.filter(
                                participant_id__in=unit_member_objs
                                )
    already_joined_members_unit = unique_group_event_by_dist.values_list(
                                    'participant__registered_user__unit_name_id',
                                    flat=True
                                ).distinct()
    print("already_joined_members_unit:",already_joined_members_unit)
    
    newly_joined_members_unit = UnitMembers.objects.filter(
                                    id__in = unit_member_objs
                                ).values_list(
                                    'registered_user__unit_name_id',
                                    flat=True
                                ).distinct()
    print("newly_joined_members_unit:",newly_joined_members_unit)

                                
    if already_joined_members_unit:
        if newly_joined_members_unit and already_joined_members_unit[0] == newly_joined_members_unit[0]:
            from_same_unit = True
        else:
            from_same_unit = False
    else:
            from_same_unit = False

    if unique_group_event_by_dist.exists():
        if from_same_unit:
            already_joined_members_count = unique_group_event_by_dist.values_list('participant_id',
                                        flat=True).distinct().count()
            remaining_slot = group_event_obj.max_allowed_limit - unique_group_event_by_dist_and_unit
            if remaining_slot < len(unit_member_objs):
                message = (
                        f"Already {unique_group_event_by_dist_and_unit} members joined. "
                        f"You can only add {remaining_slot} members to this event."
                        )
                data_saved = False
                return message, data_saved
    
    team_count_group = unique_group_event_by_dist.values_list('group_event__id',
                                                          flat=True).distinct()

    team_count_group_count = team_count_group.count()
    if team_count_group_count >= 2:
        message = "Only 2 teams from each district can participate in this category of Group Event."
        data_saved = False
        return message, data_saved
    
    team_group_member_duplicates = unique_group_event_by_dist.filter(
                                    participant_id__in = unit_member_objs,
                                    )
    
    if team_group_member_duplicates.exists():
        message = "Some members has been already in this event, please check again"
        data_saved = False
        return message, data_saved

    event_name = group_event_obj.name
    formatted_event_name = re.sub(r"[()]", "", event_name)
    formatted_event_name = "".join([word[0] for word in formatted_event_name.split()])

    if not unique_group_event_ids.exists():
        chest_number = f"{formatted_event_name}-1"
    else:
        existing_chest_number = unique_group_event_ids.last().chest_number
        if from_same_unit:
            chest_number=existing_chest_number
        else:
            split_chest_number = existing_chest_number.split('-')
            latest_chest_number = int(split_chest_number[1])
            chest_number = f"{formatted_event_name}-{latest_chest_number+1}"
            
    
    print("Chest Number Individual Initial:",chest_number)

    try:
        participation_objs = [
            GroupEventParticipation.objects.create(
                group_event=group_event_obj,
                participant_id=unit_member,
                chest_number=chest_number,
                added_by=request.user
            )
            for unit_member in unit_member_objs
        ]
        
        GroupEvent.objects.filter(id=group_event_obj.id).update(
            per_unit_allowed_limit=F('per_unit_allowed_limit') - 1
        )
        
        message = "Participant(s) successfully added to the group event."
        data_saved = True
        return message, data_saved

    except Exception as e:
        print("Exception:", str(e))
        message = "Some error occured, Please try again later"
        data_saved = False
        return message, data_saved


def remove_group_event_participant_from_event(request, event_id, participant_id):
    try:
        group_event_participant = GroupEventParticipation.objects.filter(
            group_event_id=event_id,
            participant_id=participant_id
        ).first()

        group_event_participant.delete()
        
        return True

    except Exception:
        return False


def view_all_individual_event_participants(request):
    individual_event_participations = IndividualEventParticipation.objects.filter(
        added_by__clergy_district_id = request.user.clergy_district_id
    ).select_related(
    'individual_event', 'participant', 'participant__registered_user', 'participant__registered_user__unit_name', 'participant__registered_user__unit_name__clergy_district'
    ).order_by('individual_event__name')
    
    individual_event_participations_custom_dict = {}
    
    for individual_event_particpant in individual_event_participations:

        event_name = individual_event_particpant.individual_event.name

        if event_name not in individual_event_participations_custom_dict:
            individual_event_participations_custom_dict[event_name] = []

        individual_event_participations_custom_dict[event_name].append({
            "individual_event_participation_id": individual_event_particpant.id,
            "individual_event_id": individual_event_particpant.individual_event_id,
            "participant_id": individual_event_particpant.participant.id,
            "participant_name": individual_event_particpant.participant.name.title(),
            "participant_unit": individual_event_particpant.participant.registered_user.unit_name.name.title(),
            "participant_district": individual_event_particpant.participant.registered_user.unit_name.clergy_district.name.title(),
            "participant_phone": individual_event_particpant.participant.number,
        })

    return individual_event_participations_custom_dict



def view_all_group_event_participants(request):
    group_event_participations_obj = GroupEventParticipation.objects.filter(
        added_by__clergy_district_id = request.user.clergy_district_id
    )
    
    group_event_participations = group_event_participations_obj.select_related(
                                'group_event',
                                'participant',
                                ).order_by('group_event__name')

    group_event_participations_custom_dict = {}

    for grp_participant in group_event_participations:
        event_name = grp_participant.group_event.name
        team_code = grp_participant.participant.registered_user.unit_name.name.title()

        # Ensure event_name points to a dictionary
        if event_name not in group_event_participations_custom_dict:
            group_event_participations_custom_dict[event_name] = {}

        if team_code not in group_event_participations_custom_dict[event_name]:
            group_event_participations_custom_dict[event_name][team_code] = []

        # Append participant details
        group_event_participations_custom_dict[event_name][team_code].append({
            "group_event_participation_id": grp_participant.id,
            "group_event_id": grp_participant.group_event_id,
            "group_event_max_allowed_limit": grp_participant.group_event.max_allowed_limit,
            "participant_unit_id": grp_participant.participant.registered_user.unit_name_id,
            "participant_id": grp_participant.participant_id,
            "participant_name": grp_participant.participant.name.title(),
            "participant_unit": grp_participant.participant.registered_user.unit_name.name.title(),
            "participant_district": grp_participant.participant.registered_user.unit_name.clergy_district.name.title(),
            "participant_phone": grp_participant.participant.number,
            "total_count": len(group_event_participations_custom_dict[event_name][team_code]) + 1
        })
    return group_event_participations_custom_dict
