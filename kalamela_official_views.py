from django.shortcuts import (render,
                              redirect)
from django.contrib.auth import (logout,
                                 login)
from django.db.models import F,Q, Count
from django.contrib import messages
from django.http import JsonResponse
import json
import os
from django.utils.timezone import localtime
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import uuid

from auth_app.models import (CustomUser,
                             ClergyDistrict,
                             UnitName,
                             UnitMembers)

from kalamela.models import (
    IndividualEvent,
    GroupEvent,
    IndividualEventParticipation,
    GroupEventParticipation,
    KalamelaPayements
)

from .utility import (
    list_all_individual_events,
    list_all_group_events,
    individual_event_members_data,
    add_individual_participant_to_event,
    group_event_members_data,
    add_group_participant_to_event,
    remove_individual_event_participant_from_event,
    remove_group_event_participant_from_event,
    view_all_individual_event_participants,
    view_all_group_event_participants)



# from conference.forms import LoginForm
# Create your views here.


def kalamela_official_home_page(request):
    individual_events = list_all_individual_events(request=request)
    group_events = list_all_group_events(request=request)

    context = {
        'individual_events': individual_events,
        'group_events': group_events,
    }
    return render(request,
                  'Kalamela/kalamela_dist_official/kalamela_official_home.html',
                  context)


def kalamela_official_select_individual_event_participant(request):
    unit_data = UnitName.objects.filter(
            clergy_district_id = request.user.clergy_district_id
            ).order_by('name')
    if request.method == "POST":
        event_id = request.POST.get("event_id")
        unit_id = request.POST.get("unit_id")
        unit_name = None

        event_obj = IndividualEvent.objects.get(id=event_id)

        unit_members = individual_event_members_data(
                                            request=request,
                                            event_obj=event_obj,
                                            unit_id=unit_id)
        if unit_id:
            unit_name = unit_members.first().registered_user.unit_name.name

        context={
            "district":request.user.clergy_district.name,
            "units": unit_data,
            "event":event_obj,
            "unit_members": unit_members.order_by('name'),
            "unit_name":unit_name
        }
        return render(request,
                  'Kalamela/kalamela_dist_official/kalamela_official_select_individual_event_participant.html',
                  context)
    else:
        return redirect(request,
                        'kalamela_official_home_page')


def kalamela_official_add_individual_event_participant(request):
    if request.method == "POST":
        event_id = request.POST.get("event_id")
        unit_member_id = request.POST.get("unit_member_id")
        seniority_category = request.POST.get("seniority_category")

        event_obj = IndividualEvent.objects.get(id=event_id)
        unit_member_obj = UnitMembers.objects.get(id=unit_member_id)

        result_message, data_saved = add_individual_participant_to_event(
                                        event_obj=event_obj,
                                        unit_member_obj=unit_member_obj,
                                        seniority_category=seniority_category,
                                        request=request)
        if data_saved:
            participant_event_count = IndividualEventParticipation.objects.filter(
                                        individual_event_id=event_id,
                                        added_by__clergy_district_id=request.user.clergy_district_id
                                        ).count()
            print("participant_event_count:", participant_event_count)
            if participant_event_count == 2:
                messages.success(request,result_message)
                return redirect('kalamela_official_view_individual_participants_list')
            else:
                unit_members = individual_event_members_data(
                                            request=request,
                                            event_obj=event_obj,)
                context={
                    "district":request.user.clergy_district.name,
                    "event":event_obj,
                    "unit_members": unit_members.order_by('name'),
                }
                return render(request,
                  'Kalamela/kalamela_dist_official/kalamela_official_select_individual_event_participant.html',
                  context)
        else:
            messages.error(request,result_message)
            return redirect('kalamela_official_home_page')
    else:
        return redirect(request,
                        'kalamela_official_home_page')


def kalamela_official_view_individual_participants_list(request):
    individual_event_participations_custom_dict = view_all_individual_event_participants(request)
    context = {
        'individual_event_participations_custom_dict': individual_event_participations_custom_dict
    }
    return render(request,
                  'Kalamela/kalamela_dist_official/kalamela_official_view_individual_event_participant.html',
                  context)


def kalamela_official_remove_individual_event_participant(request):
    if request.method == "POST":
        event_id = request.POST.get("event_id")
        participant_id = request.POST.get("participant_id")

        response = remove_individual_event_participant_from_event(
            request=request,
            event_id=event_id,
            participant_id=participant_id
        )

        if response:
            message = 'Participant has been successfully removed from event'
            messages.success(request,message)
            return redirect('kalamela_official_view_individual_participants_list')
        else:
            message = 'some error occured, please try again later'
            messages.error(request,message)
            return redirect('kalamela_official_view_individual_participants_list')


def kalamela_official_select_group_event_participants(request):
    unit_data = UnitName.objects.filter(
            clergy_district_id = request.user.clergy_district_id
            ).order_by('name')

    if request.method == "POST":
        district_id = request.user.clergy_district.id
        event_id = request.POST.get("event_id")
        unit_id = request.POST.get("unit_id")
        unit_name = None
        rem_slot = None

        event_obj = GroupEvent.objects.get(id=event_id)

        already_registered_events = (
        GroupEventParticipation.objects
        .select_related('participant__registered_user__unit_name', 'participant__registered_user', 'participant')
        )

        unit_wise_particpants_count = already_registered_events.filter(
                            group_event_id=event_id,
                            participant__registered_user__unit_name__id=unit_id).count()

        print('already_registered_events',already_registered_events)
        print('unit_wise_count', unit_wise_particpants_count)


        unit_members = group_event_members_data(
                                            request=request,
                                            event_obj=event_obj,
                                            unit_id=unit_id)
        if unit_id:
            unit_name = unit_members.first().registered_user.unit_name.name

        if already_registered_events.exists():
            rem_slot = event_obj.max_allowed_limit - unit_wise_particpants_count
        else:
            rem_slot = event_obj.max_allowed_limit

        print("rem_slot", rem_slot)

        context={
            "district":request.user.clergy_district.name,
            "units":unit_data,
            "event":event_obj,
            "unit_members": unit_members.order_by('name'),
            "unit_name":unit_name,
            "unit_id":unit_id,
            "rem_slot":rem_slot,
            "unit_wise_particpants_count":unit_wise_particpants_count
        }
        return render(request,
                  'Kalamela/kalamela_dist_official/kalamela_official_select_group_event_participants.html',
                  context)
    else:
        return redirect('kalamela_official_home_page')


def kalamela_official_add_group_event_participant(request):
    if request.method == "POST":
        data = json.loads(request.body)
        event_id = data.get("event_id")
        unit_member_ids = data.get("unit_member_ids")
        print('unit_member_ids:', unit_member_ids)
        unit_id = data.get("unit_id")
        print('unit_id:', unit_id)

        event_obj = GroupEvent.objects.get(id=event_id)

        message, data_saved = add_group_participant_to_event(
            group_event_obj=event_obj,
            unit_id=unit_id,
            unit_member_objs=unit_member_ids,
            request=request
        )

        if data_saved:
            return JsonResponse({"success": True,
                                 "message": message},
                                 status=200)
        else:
            return JsonResponse({"success": False,
                                 "message": message},
                                 status=400)

    return JsonResponse({"success": False,
                         "message": "Invalid request method."},
                        status=405)


def kalamela_official_view_group_participants_list(request):
    group_event_participations_custom_dict = view_all_group_event_participants(request)
    context = {
        'group_event_participations_custom_dict': group_event_participations_custom_dict,
    }
    return render(request, 'Kalamela/kalamela_dist_official/kalamela_official_view_group_event_participant.html', context)


def kalamela_official_remove_group_event_participant(request):
    if request.method == "POST":
        event_id = request.POST.get("event_id")
        participant_id = request.POST.get("participant_id")

        response = remove_group_event_participant_from_event(
            request=request,
            event_id=event_id,
            participant_id=participant_id
        )

        if response:
            message = 'Participant has been successfully removed from event'
            messages.success(request,message)
            return redirect('kalamela_official_view_group_participants_list')
        else:
            message = 'some error occured, please try again later'
            messages.error(request,message)
            return redirect('kalamela_official_view_group_participants_list')


def kalamela_official_view_events_preview(request):
    individual_event_participations = view_all_individual_event_participants(request)
    group_event_participations = view_all_group_event_participants(request)

    total_group_events = []
    for event in group_event_participations.keys():
        for team_code in group_event_participations[event].keys():
            total_group_events.append(team_code)


    individual_events_count = IndividualEventParticipation.objects.filter(
        added_by__clergy_district_id=request.user.clergy_district_id
    ).count()

    group_events_count = len(total_group_events)
    individal_event_amount = individual_events_count * 50
    group_event_amount = group_events_count * 100
    total_amount_to_pay = individal_event_amount + group_event_amount

    kalamela_payment = KalamelaPayements.objects.filter(
                paid_by__clergy_district_id=request.user.clergy_district_id).first()
    context={
        "individual_event_participations" : individual_event_participations,
        "group_event_participations": group_event_participations,
        "individual_events_count":individual_events_count,
        "group_events_count": group_events_count,
        "individal_event_amount":individal_event_amount,
        "group_event_amount":group_event_amount,
        "total_amount_to_pay":total_amount_to_pay,
        "kalamela_payment":kalamela_payment
    }
    return render(request,
                  'Kalamela/kalamela_dist_official/kalamela_official_view_events_preview.html',
                  context)


def kalamela_official_make_payment(request):
    if request.method == "POST":
        individual_events_count = request.POST.get('individual_events_count')
        group_events_count = request.POST.get('group_events_count')
        total_amount_to_pay = request.POST.get('total_amount_to_pay')
        try:
            KalamelaPayements.objects.create(
                paid_by=request.user,
                individual_events_count=individual_events_count,
                group_events_count=group_events_count,
                total_amount_to_pay=total_amount_to_pay,
                payment_status='Pending, No Proof Uploaded'
            )
            message = "Payment Completed Successfully. Please wait for verification from Admin."
            messages.success(request, message)
            return redirect ('kalamela_official_view_events_preview')
        except Exception:
            message = "Some error occured, please try again"
            messages.error(request, message)
            return redirect ('kalamela_official_view_events_preview')
    else:
        return redirect ('kalamela_official_view_events_preview')


def kalamela_official_payment_proof_upload(request):
    if request.method == "POST":
        payment_id = request.POST.get('payment_id')

        try:
            # Ensure that the KalamelaPayements object exists
            kalamela_payments = KalamelaPayements.objects.get(id=payment_id)

            payment_proof = request.FILES.get('payment_proof')
            if payment_proof:
                # Get the current date in YYYY_MM_DD format
                current_date = localtime().strftime('%Y_%m_%d')

                # Extract the file extension (e.g., .jpg, .png)
                file_extension = os.path.splitext(payment_proof.name)[1]

                # Add a unique identifier to avoid filename conflicts
                unique_filename = f"{current_date}_{uuid.uuid4().hex}{file_extension}"

                # Use Django's FileSystemStorage to save the file
                fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads/Kalamela Payments'))
                filename = fs.save(unique_filename, payment_proof)
                file_url = fs.url(filename)

                # Update the model with the new file and status
                kalamela_payments.payment_proof = unique_filename
                kalamela_payments.payment_status = 'Pending, Proof Uploaded'
                kalamela_payments.save()

                # Provide success message
                message = "Payment Proof Uploaded Successfully. Please wait for verification from Admin."
                messages.success(request, message)
                return redirect('kalamela_official_view_events_preview')

            else:
                message = "No payment proof uploaded."
                messages.error(request, message)
                return redirect('kalamela_official_view_events_preview')

        except KalamelaPayements.DoesNotExist:
            message = "Payment ID not found."
            messages.error(request, message)
            return redirect('kalamela_official_view_events_preview')

        except Exception as e:
            # Log the error message for debugging (optional)
            print(f"Error: {e}")
            message = "An error occurred during payment proof upload."
            messages.error(request, message)
            return redirect('kalamela_official_view_events_preview')


def kalamela_official_print_form(request):
    individual_event_participations = view_all_individual_event_participants(request)
    group_event_participations = view_all_group_event_participants(request)
    kalamela_payment = KalamelaPayements.objects.filter(
                paid_by__clergy_district_id=request.user.clergy_district_id).first()

    context={
        "individual_event_participations" : individual_event_participations,
        "group_event_participations": group_event_participations,
        "kalamela_payment":kalamela_payment
    }
    return render(request,
                  'Kalamela/kalamela_dist_official/kalamela_official_print_form2.html',
                  context)