from django.shortcuts import (render,
                              redirect)
from django.contrib.auth import (authenticate,
                                 logout,
                                 login)
from django.db.models import Q
from django.contrib import messages
from django.db.models import Count,Sum
from auth_app.models import (CustomUser,
                             UnitMembers)
from kalamela.models import (IndividualEventParticipation,
                             GroupEventParticipation,
                             KalamelaPayements,
                             IndividualEvent,
                             GroupEvent,
                             IndividualEventScoreCard,
                             GroupEventScoreCard,
                             Appeal,
                             AppealPayements)

def kalamela_home_page(request):
    return render(request, "Kalamela/kalamela_home_page.html")

def kalamela_find_participants(request):
    if request.method == "POST":
        chest_number = request.POST.get("chest_number")
        individual_participants = IndividualEventParticipation.objects.filter(chest_number=chest_number)
        group_participants = GroupEventParticipation.objects.filter(chest_number=chest_number)

        if not individual_participants.exists() and not group_participants.exists():
            message = "Not Exists"
            messages.error(request, message)
            return redirect('kalamela_home_page')

        context = {
            "individual_participants": individual_participants,
            "group_participants": group_participants
        }
        return render(request, "Kalamela/kalamela_find_participants.html", context)

    else:
        return redirect('kalamela_home_page')


def kalamela_results(request):
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
        # Fetch top 3 results for the event
        
        individual_event_scores = IndividualEventScoreCard.objects.filter(
            event_participation__individual_event__name=event,
        ).exclude(added_on__isnull=True).select_related(
            'event_participation'
        ).order_by(
            'added_on',
            '-total_points'
        )[:3]  # Limit to the top 3 for each event
        
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
        )[:3]
        
        for data in group_event_scores:
            participations = GroupEventParticipation.objects.filter(
                chest_number=data.chest_number
            ).first()
            if participations:
                data.unit = participations.participant.registered_user.unit_name.name
                data.district = participations.participant.registered_user.unit_name.clergy_district.name
            else:
                data.unit = None
                data.district = None
        
        if group_event_scores.count() == 0:
            pass 
        else:
            group_results_dict[event] = group_event_scores
    
    
    
    context = {
        "results_dict": indivdiual_results_dict,
        "group_results_dict":group_results_dict,
    }
    

    return render(request, "Kalamela/kalamela_results.html", context)

from datetime import datetime
from django.utils import timezone
from datetime import timedelta

def kalamela_appeal_form(request):
    if request.method == "POST":
        chest_number = request.POST.get("chest_number")
        event_name = request.POST.get("event_name")
        individual_event = IndividualEvent.objects.filter(name=event_name).first()
        group_event = GroupEvent.objects.filter(name=event_name).first()
        
        individual_participants = None
        group_participants = None
        saved_time = None
        
        if individual_event:
            individual_participants = IndividualEventScoreCard.objects.filter(
                                        event_participation__individual_event_id=individual_event.id,
                                        event_participation__chest_number=chest_number).first()
            if individual_participants:
                saved_time = individual_participants.added_on

        if group_event:
            group_participants = GroupEventScoreCard.objects.filter(
                                        event_participation__group_event_id=group_event.id,
                                        event_participation__chest_number=chest_number).first()
            if group_participants:
                saved_time = group_participants.added_on
        
        if not individual_participants and not group_participants:
            message = "Wrong Info"
            messages.error(request, message)
            return redirect('kalamela_results')
        
        if saved_time:
            current_time = timezone.now()
            time_difference = current_time - saved_time
            if time_difference > timedelta(minutes=30):
                message = "Sorry, You cannot raise appeal after 30 minutes of result publication."
                messages.error(request,message)
                return redirect('kalamela_results')
        
        context = {
            "individual_participants": individual_participants,
            "group_participants": group_participants
        }
        return render(request, "Kalamela/kalamela_appeal_form.html", context)

    else:
        return redirect('kalamela_results')


def kalamela_appeal_form_submission(request):
    if request.method == "POST":
        added_by_id = request.POST.get('participant_id')
        chest_number = request.POST.get('chest_number') 
        event_name = request.POST.get('event_name')  
        statement = request.POST.get('statement')
        payment_type=request.POST.get('payment_method')
        
        participant_id = UnitMembers.objects.get(id=added_by_id)
        
        if not participant_id:
            message = "No Participant Data Found!"
            messages.error(request, message)
            return redirect('kalamela_results')
        
        appeal_data, created = Appeal.objects.get_or_create(
        added_by=participant_id,
        chest_number=chest_number,
        event_name=event_name,
        defaults={
            'statement': statement,
            'status': "Added, Not Confirmed."
            }
        )

        if not created:
            message = "Appeal Already Exist!"
            messages.error(request, message)
            return redirect('kalamela_results')
        
        appeal_payment = AppealPayements.objects.create(
            appeal=appeal_data,
            total_amount_to_pay=1000,
            payment_type=payment_type,
            payment_status="Confirmation Pending."
        )
        
        message = "Appeal Added Successfully"
        messages.error(request, message)
        return redirect('kalamela_view_appeals')
    else:
        return redirect('kalamela_results')
        
        

def kalamela_view_appeals(request):
    appeals = AppealPayements.objects.filter(
        payment_status__exact="Confirmation Pending.",
        ).exclude(appeal__reply__exact=None).order_by('created_on')
    context={
        "appeals": appeals
    }
    return render(request,
                  'Kalamela/kalamela_view_appeals.html',
                  context)

def kalamela_view_kalaprathibha(request):    
    from django.db.models import Count,Sum
    kalathilakam_top = IndividualEventScoreCard.objects.filter(
    participant__gender='F',
    total_points__gte=2
    ).values('participant__name') \
        .annotate(participant_count=Count('participant')) \
        .filter(participant_count__gte=2) \
        .annotate(combined_score=Sum('total_points')) \
        .order_by('-combined_score').first()
        
    kalathilam_obj = IndividualEventScoreCard.objects.filter(
        participant__name=kalathilakam_top['participant__name']
    ).first()
    kalathilam_obj.combined_score = kalathilakam_top['combined_score']


    kalaparthiba_top = IndividualEventScoreCard.objects.filter(
    participant__gender='M',
    total_points__gte=2
    ).values('participant__name') \
        .annotate(participant_count=Count('participant')) \
        .filter(participant_count__gte=2) \
        .annotate(combined_score=Sum('total_points')) \
        .order_by('-combined_score').first()
        
    kalaparthiba_obj = IndividualEventScoreCard.objects.filter(
        participant__name=kalaparthiba_top['participant__name']
    ).first()
    kalaparthiba_obj.combined_score = kalaparthiba_top['combined_score']
    
    context = {
        'kalaparthiba_obj':kalaparthiba_obj,
        'kalathilam_obj': kalathilam_obj
    }
    
    return render(request,
                  'Kalamela/kalamela_view_kalaprathibha.html',
                  context)
    

def kalamela_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Authenticate user using Django's built-in authentication system
        user = authenticate(request, email=username, password=password)

        if user is not None:
            # Login the user and redirect based on user type
            login(request, user)
            if user.user_type == "1":  # Admin
                return redirect("kalamela_admin_home_page")
            elif user.user_type == "3":  # District Official
                kalamela_payment = KalamelaPayements.objects.filter(
                paid_by__clergy_district_id=user.clergy_district_id).first()
                if not kalamela_payment:
                    return redirect("kalamela_official_home_page")
                else:
                    return redirect("kalamela_official_view_events_preview")
            else:
                messages.error(request, "Invalid User Type")
                return redirect("kalamela_login")
        else:
            # Authentication failed
            messages.error(request, "Invalid username or password")
            return redirect("kalamela_login")

    return render(request, "Kalamela/kalamela_home_page.html")


def kalamela_logout(request):
    logout(request)
    return redirect("kalamela_login")
