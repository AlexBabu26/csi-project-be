from django.shortcuts import (render,
                              redirect,
                              get_object_or_404)
from django.contrib.auth import (logout,
                                 login)
from django.db.models import Q
from django.contrib import messages
from datetime import date
import json
from django.http import JsonResponse
from django.urls import reverse
from django.conf import settings
from django.db.models import Count,Sum

from auth_app.models import (CustomUser,
                             ClergyDistrict,
                             UnitName,
                             UnitMembers)

from kalamela.models import (
    IndividualEvent,
    GroupEvent,
    IndividualEventParticipation,
    GroupEventParticipation,
    KalamelaExcludeMembers,
    KalamelaPayements,
    IndividualEventScoreCard,
    GroupEventScoreCard,
    Appeal,
    AppealPayements,
)

from kalamela.forms import (IndividualEventForm,
                            GroupEventForm,
                            UnitMembersForm)

from .admin_utility import (view_all_group_event_participants,
                            view_all_individual_event_participants,
                            admin_export_all_events_data,
                            admin_export_all_chest_numbers,
                            export_all_results)


def kalamela_admin_home_page(request):
    individual_events = IndividualEvent.objects.all()
    group_events = GroupEvent.objects.all()
    individual_events_form = IndividualEventForm()
    group_events_form = GroupEventForm()

    context = {
        'individual_events': individual_events,
        'group_events': group_events,
        'individual_events_form': individual_events_form,
        'group_events_form': group_events_form,
    }
    return render(request,
                  'Kalamela/kalamela_admin/kalamela_admin_home.html',
                  context)


def kalamela_admin_view_all_units(request):
    unit_name_objs = UnitName.objects.all(
        ).order_by('clergy_district__name', 'name')
    context={"unit_name_objs":unit_name_objs}
    return render(request,
                    'Kalamela/kalamela_admin/kalamela_admin_view_all_unit.html',
                    context)


def kalamela_admin_view_all_unit_members(request):
    if request.method == "POST":

        already_excluded_members_list = KalamelaExcludeMembers.objects.all(
                                        ).values_list('members__name', flat=True)
        unit_id = request.POST.get('unit_id')
        unit_obj = UnitName.objects.get(id=unit_id)
        unit_members = UnitMembers.objects.filter(
            registered_user__unit_name_id=unit_id
        )
        unit_members_data = {}
        unit_members_count = unit_members.count()
        unit_name = ""

        for i in unit_members:
            dob = i.dob
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            unit_members_data.update({i: age})
            unit_name = i.registered_user.username

        context = {
            "unit_members_data": unit_members_data,
            "unit_members_count": unit_members_count,
            "unit_name": unit_obj.name,
            "already_excluded_members_list":already_excluded_members_list
        }

        return render(request,
                    'Kalamela/kalamela_admin/kalamela_admin_view_all_unit_members.html',
                    context)
    else:
        return redirect('kalamela_admin_home_page')


def kalamela_admin_edit_unit_members(request,unit_member_id):
    unit_member = get_object_or_404(UnitMembers, id=unit_member_id)
    if request.method == "POST":
        form = UnitMembersForm(request.POST, instance=unit_member)
        if form.is_valid():
            form.save()
            message = "Unit Member datails has been successfully updated"
            messages.success(request,
                             message)
            return redirect('kalamela_admin_view_all_units')
    else:
        form = UnitMembersForm(instance=unit_member)
        return render(request,
                      'Kalamela/kalamela_admin/kalamela_admin_edit_unit_member.html',
                      {"form":form,
                       "unit_member":unit_member,
                       "already_excluded_members_list":already_excluded_members_list})


def kalamela_admin_exclude_unit_member(request):
    if request.method == "POST":
        unit_member_id = request.POST.get('unit_member_id')
        unit_member=UnitMembers.objects.get(id=unit_member_id)
        KalamelaExcludeMembers.objects.create(
            members=unit_member
        )

        message=f"{unit_member.name} has been excluded from all events"
        messages.success(request,
                         message)
        return redirect('kalamela_admin_view_all_excluded_members')
    else:
        return redirect('kalamela_admin_view_all_units')


def kalamela_admin_view_all_excluded_members(request):
    excluded_members = KalamelaExcludeMembers.objects.all()
    if request.method=="POST":
        exclude_user_id=request.POST.get('exclude_user_id')
        exclude_user_obj = excluded_members.get(id=exclude_user_id)
        exclude_user_obj.delete()
        message = "Successfully removed from excluded list"
        messages.success(request,
                         message)
        return redirect('kalamela_admin_view_all_excluded_members')

    context={
        "excluded_members":excluded_members
    }
    print(excluded_members)
    return render(request,
                  'Kalamela/kalamela_admin/kalamela_admin_view_all_excluded_members.html',
                  context)


def kalamela_admin_add_individual_event(request):
    if request.method == 'POST':
        individual_events_form = IndividualEventForm(request.POST)
        if individual_events_form.is_valid():
            individual_events_form.save()
            message = 'Success'
            messages.success(request, message)
            return redirect('kalamela_admin_home_page')
        else:
            message = 'some error occured, please try again later'
            messages.error(request, message)
            return redirect('kalamela_admin_home_page')


def kalamela_admin_update_individual_event(request, event_id=None):
    if event_id:
        individual_event = IndividualEvent.objects.get(id=event_id)
        individual_events_update_form = IndividualEventForm(
                                    request.POST,
                                    instance=individual_event)
        if request.method == "POST":
            if individual_events_update_form.is_valid():
                individual_events_update_form.save()
                message = 'Changes has been updated successfully'
                messages.success(request, message)
                return redirect('kalamela_admin_home_page')
            else:
                message = 'some error occured, please try again later'
                messages.error(request, message)
                return redirect('kalamela_admin_home_page')
        else:
            individual_events_update_form = IndividualEventForm(
                                                instance=individual_event)
            return render(request,
                          'Kalamela/kalamela_admin/kalamela_admin_home.html.html', {'form': individual_events_form, 'event_id': event_id})


def kalamela_admin_add_group_event(request):
    if request.method == 'POST':
        group_events_form = GroupEventForm(request.POST)
        if group_events_form.is_valid():
            group_events_form.save()
            message = 'Success'
            messages.success(request, message)
            return redirect('kalamela_admin_home_page')
        else:
            message = 'some error occured, please try again later'
            messages.error(request, message)
            return redirect('kalamela_admin_home_page')


def kalamela_admin_update_group_event(request, event_id=None):
    if event_id:
        group_event = GroupEvent.objects.get(id=event_id)
        group_events_form = GroupEventForm(
                                request.POST,
                                instance=group_event)
        if request.method == 'POST':
            if group_events_form.is_valid():
                group_events_form.save()
                message = 'Changes has been updated successfully'
                messages.success(request, message)
                return redirect('kalamela_admin_home_page')
            else:
                message = 'some error occured, please try again later'
                messages.error(request, message)
                return redirect('kalamela_admin_home_page')


def kalamela_admin_view_individual_participants_list(request):
    individual_event_participations = IndividualEventParticipation.objects.all().select_related(
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
            "participant_chest_number": individual_event_particpant.chest_number,
        })

    context = {
        "individual_event_participations_custom_dict": individual_event_participations_custom_dict
    }

    return render(request,
                 'Kalamela/kalamela_admin/kalamela_admin_view_individual_event_participant.html',
                 context)


def kalamela_admin_view_group_participants_list(request):
    group_event_participations = GroupEventParticipation.objects.all(
    ).select_related(
    'group_event', 'participant', 'participant__registered_user', 'participant__registered_user__unit_name', 'participant__registered_user__unit_name__clergy_district'
    ).order_by('group_event__name','chest_number')

    group_event_participations_custom_dict = {}

    for grp_participant in group_event_participations:
        event_name = grp_participant.group_event.name
        team_code = grp_participant.participant.registered_user.unit_name.name

        # Ensure event_name points to a dictionary
        if event_name not in group_event_participations_custom_dict:
            group_event_participations_custom_dict[event_name] = {}

        if team_code not in group_event_participations_custom_dict[event_name]:
            group_event_participations_custom_dict[event_name][team_code] = []

        # Append participant details
        group_event_participations_custom_dict[event_name][team_code].append({
            "group_event_participation_id": grp_participant.id,
            "group_event_id": grp_participant.group_event_id,
            "participant_id": grp_participant.participant_id,
            "participant_name": grp_participant.participant.name.title(),
            "participant_unit": grp_participant.participant.registered_user.unit_name.name.title(),
            "participant_district": grp_participant.participant.registered_user.unit_name.clergy_district.name.title(),
            "participant_phone": grp_participant.participant.number,
            "participant_chest_number": grp_participant.chest_number,
        })

    context = {
        'group_event_participations_custom_dict':group_event_participations_custom_dict,
    }
    return render(request,
                  'Kalamela/kalamela_admin/kalamela_admin_view_group_event_participant.html',
                  context)


def kalamela_edit_chest_number(request):
    if request.method == "POST":
        event_participation_id=request.POST.get("event_participation_id")
        chest_number = request.POST.get('chest_number')
        try:
            gp = GroupEventParticipation.objects.get(id=event_participation_id)
            gp.chest_number=chest_number
            gp.save()
            message="Updated Succcessfully"
            messages.success(request, message)
            return redirect('kalamela_admin_view_group_participants_list')
        except Exception as e:
            print("Exception:", str(e))
            message="Update Failed"
            messages.error(request, message)
            return redirect('kalamela_admin_view_group_participants_list')
    else:
        return redirect('kalamela_admin_view_group_participants_list')


def kalamela_admin_view_events_preview(request):
    individual_event_objs = IndividualEvent.objects.all()
    group_event_objs = GroupEvent.objects.all()
    clergy_district_objs = ClergyDistrict.objects.all()
    individual_events_scores = IndividualEventScoreCard.objects.all(
                                ).values_list('event_participation__individual_event__name',
                                              flat=True).distinct()
    group_events_scores = GroupEventScoreCard.objects.all(
                                ).values_list('event_name',
                                              flat=True).distinct()
    individual_event_participations = view_all_individual_event_participants(
                                        request=request,district_id=None)
    group_event_participations = view_all_group_event_participants(
                                        request=request,district_id=None)
    individual_events_count = IndividualEventParticipation.objects.all().count()
    district=None
    district_id=None

    if request.method == "POST":
        district_id = request.POST.get('district_id')
        individual_event_participations = view_all_individual_event_participants(
                                                request=request,district_id=district_id)
        group_event_participations = view_all_group_event_participants(
                                                request=request,district_id=district_id)
        district=clergy_district_objs.filter(id=district_id).first()

        individual_events_count = IndividualEventParticipation.objects.filter(
        added_by__clergy_district_id=district_id
        ).count()

    total_group_events = []
    for event in group_event_participations.keys():
        for team_code in group_event_participations[event].keys():
            total_group_events.append(team_code)

    group_events_count = len(total_group_events)
    individal_event_amount = individual_events_count * 50
    group_event_amount = group_events_count * 100
    total_amount_to_pay = individal_event_amount + group_event_amount

    # kalamela_payment = KalamelaPayements.objects.filter(
    #             paid_by__clergy_district_id=request.user.clergy_district_id).first()

    context={
        "clergy_districts":clergy_district_objs,
        "individual_events":individual_event_objs,
        "group_events":group_event_objs,
        "district":district,
        "individual_event_participations" : individual_event_participations,
        "group_event_participations": group_event_participations,
        "individual_events_count":individual_events_count,
        "group_events_count": group_events_count,
        "individal_event_amount":individal_event_amount,
        "group_event_amount":group_event_amount,
        "total_amount_to_pay":total_amount_to_pay,
        # "kalamela_payment":kalamela_payment,
        "individual_events_scores": list(individual_events_scores),
        "group_events_scores": list(group_events_scores)
    }
    return render(request,
                  'Kalamela/kalamela_admin/kalamela_admin_view_events_preview.html',
                  context)


def kalamela_admin_view_payments(request):
    kalamela_payments = KalamelaPayements.objects.all().order_by('-created_on')
    context = {
       "kalamela_payments":kalamela_payments
    }

    return render(request,
                  'Kalamela/kalamela_admin/kalamela_admin_view_payments.html',
                  context)


def kalamela_admin_invalid_payment_proof(request):
    if request.method=="POST":
        try:
            payment_id = request.POST.get('payment_id')
            kalamela_payments = KalamelaPayements.objects.get(id=payment_id)
            kalamela_payments.payment_status = "Pending, No Proof Uploaded"
            kalamela_payments.payment_proof=None
            kalamela_payments.save()
            message="Payment Proof Declined Successfully"
            messages.success(request, message)
            return redirect('kalamela_admin_view_payments')
        except Exception as e:
            print(f"EXCEPTION: {e}" )
            message="Some error occured"
            messages.error(request, message)
            return redirect('kalamela_admin_view_payments')
    else:
        return redirect('kalamela_admin_view_payments')


def kalamela_admin_approve_payment(request):
    if request.method=="POST":
        try:
            payment_id = request.POST.get('payment_id')
            kalamela_payments = KalamelaPayements.objects.get(id=payment_id)
            kalamela_payments.payment_status = "Paid"
            kalamela_payments.save()
            message="Payment Approved Successfully"
            messages.success(request, message)
            return redirect('kalamela_admin_view_payments')
        except Exception as e:
            print(f"EXCEPTION: {e}" )
            message="Some error occured"
            messages.error(request, message)
            return redirect('kalamela_admin_view_payments')
    else:
        return redirect('kalamela_admin_view_payments')


def kalamela_admin_export_all_events_data(request):
    district_id = None
    individual_event=None
    group_event=None
    if request.method == "POST":
        district_id = request.POST.get('district_id')
        individual_event = request.POST.get('individual_event')
        group_event = request.POST.get('group_event')

        district_id = None if district_id == 'all' else district_id
        individual_event = None if individual_event == 'all' else individual_event
        group_event = None if group_event == 'all' else group_event

        if district_id:
            district_id=district_id
        if individual_event:
            individual_event=individual_event
        if group_event:
            group_event=group_event

        response = admin_export_all_events_data(
            request=request,
            district_id=district_id,
            individual_event=individual_event,
            group_event=group_event
        )
        message="Exported Successfully"
        messages.success(request, message)
        return response


def kalamela_admin_export_all_chest_numbers(request):
    if request.method == "POST":
        district_id=request.POST.get("district_id")
        if not district_id:
            district_id = None
        response = admin_export_all_chest_numbers(request=request)
        message="Expoted Successfully"
        messages.success(request,message)
        return response
    else:
        return redirect('kalamela_admin_view_events_preview')


def kalamela_admin_individual_events_candidates(request):
    if request.method == "POST":
        individual_event_participation_name=request.POST.get("individual_event_participation_name")
        individual_event_participation_objs = IndividualEventParticipation.objects.filter(
            individual_event__name=individual_event_participation_name).order_by('chest_number')
        context={
            "individual_event_participations":individual_event_participation_objs,
            "event_name":individual_event_participation_objs.first().individual_event.name
        }
        return render(request,
                      "Kalamela/kalamela_admin/kalamela_admin_individual_events_candidates.html",
                      context)
    else:
        return redirect('kalamela_admin_view_events_preview')


def kalamela_admin_add_individual_events_score(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            participants = body.get('participants', [])
            scorecards = []

            for entry in participants:
                event_participation_id = entry['event_participation_id']
                chest_number = entry['chest_number']
                participant_name = entry['participant_name']
                awarded_marks = entry['awarded_marks']
                grade = entry['grade']
                points = entry['points']

                participant_id = IndividualEventParticipation.objects.get(
                                    id=event_participation_id
                                    ).participant_id

                # Create the IndividualEventScoreCard instance and add it to the list
                scorecard = IndividualEventScoreCard(
                    event_participation_id=event_participation_id,
                    participant_id=participant_id,
                    awarded_mark=awarded_marks,
                    grade=grade,
                    total_points=points
                )
                scorecards.append(scorecard)
            IndividualEventScoreCard.objects.bulk_create(scorecards)
            redirect_url = reverse('kalamela_admin_view_events_score')
            full_redirect_url = settings.SITE_URL + redirect_url
            print("full_redirect_url:", full_redirect_url)
            return JsonResponse({"status": "success",
                                 "message": "Data received successfully!",
                                 "redirect_url": full_redirect_url})
        except json.JSONDecodeError:
            redirect_url = reverse('kalamela_admin_view_events_preview')
            full_redirect_url = settings.SITE_URL + redirect_url
            return JsonResponse({"status": "error",
                                 "message": "Invalid JSON data!",
                                 "redirect_url":full_redirect_url})
    return redirect('kalamela_admin_view_events_preview')


def kalamela_admin_view_events_score(request):

    indivdiual_results_dict = {}
    # Fetch distinct individual event names
    individual_events = IndividualEvent.objects.all().values_list(
        'name',
        flat=True
    ).distinct()

    group_results_dict = {}
    group_events = GroupEvent.objects.all().values_list(
        'name',
        flat=True
    ).distinct()

    for event in individual_events:
        individual_event_scores = IndividualEventScoreCard.objects.filter(
            event_participation__individual_event__name=event,
        ).exclude(added_on__isnull=True).select_related(
            'event_participation'
        ).order_by(
            '-total_points'
        )

        if individual_event_scores.count() == 0:
            pass
        else:
            indivdiual_results_dict[event] = individual_event_scores


    for event in group_events:
        # Fetch top 3 results for the event

        group_event_scores = GroupEventScoreCard.objects.filter(
            event_name=event,
        ).exclude(added_on__isnull=True).order_by(
            '-total_points'
        )

        if group_event_scores.count() == 0:
            pass
        else:
            group_results_dict[event] = group_event_scores

    context = {
        "results_dict": indivdiual_results_dict,
        "group_results_dict":group_results_dict
    }

    return render(request,
                  "Kalamela/kalamela_admin/kalamela_admin_view_events_score.html",
                  context)


def kalamela_admin_view_appeals(request):
    appeals = AppealPayements.objects.all().order_by('created_on')
    context={
        "appeals": appeals
    }
    return render(request,
                  'Kalamela/kalamela_admin/kalamela_admin_view_appeals.html',
                  context)


def kalamela_admin_view_appeals_action(request):
    if request.method == "POST":
        appeal_id = request.POST.get('appeal_id')
        reply = request.POST.get('reply')

        if not appeal_id or not reply:
            return JsonResponse({"status": "error", "message": "Missing appeal_id or reply"})

        try:
            appeal_data_obj = Appeal.objects.get(id=appeal_id)
            appeal_data_obj.reply = reply
            appeal_data_obj.status = "Approved"
            appeal_data_obj.save()

            appeal_payment = AppealPayements.objects.get(appeal=appeal_data_obj)
            appeal_payment.status = "PAID"
            appeal_payment.save()

            event_name = appeal_data_obj.event_name
            kalamela_admin_update_individual_event_scorecard(event=event_name)
            return redirect('kalamela_admin_view_appeals')

        except Appeal.DoesNotExist:
            message = "message Appeal not found"
            messages.success(request, message )
            return redirect('kalamela_admin_view_appeals')
        except AppealPayements.DoesNotExist:
            message = "message Appeal Payments not found"
            messages.success(request, message )
            return redirect('kalamela_admin_view_appeals')
        except Exception as e:
            message = "an error occured"
            messages.success(request, message )
            return redirect('kalamela_admin_view_appeals')

    else:
        return redirect('kalamela_admin_view_appeals')


def kalamela_admin_view_update_individual_event_scorecard(request):
    if request.method == "POST":
        event_name = request.POST.get('event_name')
        individual_event_scores = IndividualEventScoreCard.objects.filter(
            event_participation__individual_event__name=event_name,
        ).exclude(added_on__isnull=True).select_related(
            'event_participation'
        ).order_by(
            '-total_points'
        )
        context = {
            "event_scores": individual_event_scores,
            "event_name": event_name
        }

        return render(request,
                      'Kalamela/kalamela_admin/kalamela_admin_update_individual_event_scorecard.html',
                      context)
    else:
        return redirect('kalamela_admin_view_appeals')


def kalamela_admin_save_updated_individual_scorecard(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            participants = body.get('participants', [])
            scorecards_to_update = []

            for entry in participants:
                event_participation_id = entry['event_participation_id']
                print("event_participation_id",event_participation_id)
                awarded_marks = entry['awarded_marks']
                grade = entry['grade']
                points = entry['points']

                participant_id = IndividualEventParticipation.objects.get(
                                    id=event_participation_id
                                    ).participant_id

                # Create the IndividualEventScoreCard instance and add it to the list
                scorecard = IndividualEventScoreCard.objects.get(
                        event_participation_id=event_participation_id
                    )

                # Update the necessary fields
                scorecard.awarded_mark = awarded_marks
                scorecard.grade = grade
                scorecard.total_points = points

                # Add the updated scorecard to the list for bulk update
                scorecards_to_update.append(scorecard)

            IndividualEventScoreCard.objects.bulk_update(scorecards_to_update, ['awarded_mark', 'grade', 'total_points'])
            redirect_url = reverse('kalamela_admin_view_events_score')
            full_redirect_url = settings.SITE_URL + redirect_url
            print("full_redirect_url:", full_redirect_url)
            return JsonResponse({"status": "success",
                                "message": "Data received successfully!",
                                "redirect_url": full_redirect_url})
        except json.JSONDecodeError:
            redirect_url = reverse('kalamela_admin_view_events_preview')
            full_redirect_url = settings.SITE_URL + redirect_url
            return JsonResponse({"status": "error",
                                "message": "Invalid JSON data!",
                                "redirect_url":full_redirect_url})
    return redirect('kalamela_admin_view_appeals')


def kalamela_admin_group_events_candidates(request):
    if request.method == "POST":
        group_event_participation_name=request.POST.get("group_event_participation_name")
        group_event_participation_objs = GroupEventParticipation.objects.filter(
            group_event__name=group_event_participation_name
            ).values('chest_number', 'group_event__name').distinct()
        context={
            "group_event_participations":group_event_participation_objs,
            "event_name":group_event_participation_objs.first()['group_event__name']
        }
        return render(request,
                      "Kalamela/kalamela_admin/kalamela_admin_group_events_candidates.html",
                      context)
    else:
        return redirect('kalamela_admin_view_events_preview')



def kalamela_admin_add_group_events_score(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            participants = body.get('participants', [])
            scorecards = []
            print("Group participants", participants)
            for entry in participants:
                event_name = entry['event_name']
                chest_number = entry['chest_number']
                awarded_marks = entry['awarded_marks']
                grade = entry['grade']
                points = entry['points']

                # Create the GroupEventScoreCard instance and add it to the list
                scorecard = GroupEventScoreCard(
                    event_name=event_name,
                    chest_number=chest_number,
                    awarded_mark=awarded_marks,
                    grade=grade,
                    total_points=points
                )
                scorecards.append(scorecard)
            GroupEventScoreCard.objects.bulk_create(scorecards)
            redirect_url = reverse('kalamela_admin_view_group_events_score')
            full_redirect_url = settings.SITE_URL + redirect_url
            print("full_redirect_url:", full_redirect_url)
            return JsonResponse({"status": "success",
                                 "message": "Data received successfully!",
                                 "redirect_url": full_redirect_url})
        except json.JSONDecodeError:
            redirect_url = reverse('kalamela_admin_view_events_preview')
            full_redirect_url = settings.SITE_URL + redirect_url
            return JsonResponse({"status": "error",
                                 "message": "Invalid JSON data!",
                                 "redirect_url":full_redirect_url})
    return redirect('kalamela_admin_view_events_preview')



def kalamela_admin_view_group_events_score(request):

    results_dict = {}
    group_events = GroupEvent.objects.all().values_list(
        'name',
        flat=True
    ).distinct()

    for event in group_events:
        # Fetch top 3 results for the event

        group_event_scores = GroupEventScoreCard.objects.filter(
            event_name=event,
        ).exclude(added_on__isnull=True).order_by(
            '-total_points'
        )

        if group_event_scores.count() == 0:
            pass
        else:
            results_dict[event] = group_event_scores

    context = {
        "results_dict": results_dict
    }

    return render(request,
                  "Kalamela/kalamela_admin/kalamela_admin_view_group_events_score.html",
                  context)


def kalamela_admin_view_update_group_event_scorecard(request):
    if request.method == "POST":
        event_name = request.POST.get('event_name')
        group_event_scores = GroupEventScoreCard.objects.filter(
            event_name=event_name,
        ).exclude(added_on__isnull=True).order_by(
            '-total_points'
        )
        context = {
            "event_scores": group_event_scores,
            "event_name": event_name
        }

        return render(request,
                      'Kalamela/kalamela_admin/kalamela_admin_update_group_event_scorecard.html',
                      context)
    else:
        return redirect('kalamela_admin_view_appeals')


def kalamela_admin_save_updated_group_event_scorecard(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            participants = body.get('participants', [])
            scorecards_to_update = []

            for entry in participants:
                awarded_marks = entry['awarded_marks']
                grade = entry['grade']
                points = entry['points']
                chest_number=entry['chest_number']

                # Create the IndividualEventScoreCard instance and add it to the list
                scorecard = GroupEventScoreCard.objects.get(
                        chest_number=chest_number
                    )

                # Update the necessary fields
                scorecard.awarded_mark = awarded_marks
                scorecard.grade = grade
                scorecard.total_points = points

                # Add the updated scorecard to the list for bulk update
                scorecards_to_update.append(scorecard)

            GroupEventScoreCard.objects.bulk_update(scorecards_to_update, ['awarded_mark', 'grade', 'total_points'])
            redirect_url = reverse('kalamela_admin_view_group_events_score')
            full_redirect_url = settings.SITE_URL + redirect_url
            print("full_redirect_url:", full_redirect_url)
            return JsonResponse({"status": "success",
                                "message": "Data received successfully!",
                                "redirect_url": full_redirect_url})
        except json.JSONDecodeError:
            redirect_url = reverse('kalamela_admin_view_events_preview')
            full_redirect_url = settings.SITE_URL + redirect_url
            return JsonResponse({"status": "error",
                                "message": "Invalid JSON data!",
                                "redirect_url":full_redirect_url})
    return redirect('kalamela_admin_view_appeals')


def kalamela_admin_export_all_scores(request):
    response = export_all_results(request=request)
    message="Expoted Successfully"
    messages.success(request,message)
    return response


def kalamela_admin_unit_wise_results(request):
    units = UnitName.objects.all()
    score_card_dict = {}
    for unit in units:
        score_card = IndividualEventScoreCard.objects.filter(
            participant__registered_user__unit_name=unit
        ).distinct().order_by('-total_points')[:3]

        if score_card.exists():
            if unit not in score_card_dict:
                score_card_dict[unit]=[]
            score_card_dict[unit].append(
                {
                    "unit_resuts":score_card
                }
            )

        context={
            "results_dict":score_card_dict
        }
    return render(request,
                    'Kalamela/kalamela_admin/kalamela_admin_unit_wise_results.html',
                    context)

def kalamela_admin_district_wise_results(request):
    districts = ClergyDistrict.objects.all()
    score_card_dict = {}
    for district in districts:
        score_card = IndividualEventScoreCard.objects.filter(
            participant__registered_user__unit_name__clergy_district=district
        ).distinct().order_by('-total_points')[:3]

        total_count = score_card.total_points_sum = score_card.aggregate(Sum('total_points'))['total_points__sum'] or 0

        if score_card.exists():
            if district not in score_card_dict:
                score_card_dict[district]=[]
            score_card_dict[district].append(
                {
                    "district_resuts":score_card
                }
            )

        context={
            "results_dict":score_card_dict
        }
    return render(request,
                    'Kalamela/kalamela_admin/kalamela_admin_district_wise_results.html',
                    context)