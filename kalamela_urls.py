from django.contrib import admin
from django.urls import path
from . import (kalamela_auth_views,
               kalamela_admin_views,
               kalamela_official_views)

urlpatterns = [
    # kalamela_auth_views urls 
    path("kalamela_login/",
          kalamela_auth_views.kalamela_login,
          name="kalamela_login"),
    
    path('kalamela_find_participants',
         kalamela_auth_views.kalamela_find_participants,
         name='kalamela_find_participants'),
    
    path('kalamela_results',
         kalamela_auth_views.kalamela_results,
         name='kalamela_results'),
    
    path('kalamela_appeal_form',
         kalamela_auth_views.kalamela_appeal_form,
         name='kalamela_appeal_form'),
    
    path('kalamela_appeal_form_submission',
         kalamela_auth_views.kalamela_appeal_form_submission,
         name='kalamela_appeal_form_submission'),
    
    path('kalamela_view_appeals',
         kalamela_auth_views.kalamela_view_appeals,
         name='kalamela_view_appeals'),
    
    path('kalamela_view_kalaprathibha',
         kalamela_auth_views.kalamela_view_kalaprathibha,
         name='kalamela_view_kalaprathibha'),

    path("kalamela_logout/",
          kalamela_auth_views.kalamela_logout,
          name="kalamela_logout"),






    # kalamela_admin_views urls

    path("kalamela_admin_home_page/",
          kalamela_admin_views.kalamela_admin_home_page,
          name="kalamela_admin_home_page"),
    
    path("kalamela_admin/kalamela_admin_view_all_units/",
          kalamela_admin_views.kalamela_admin_view_all_units,
          name="kalamela_admin_view_all_units"),

    path("kalamela_admin/kalamela_admin_view_all_unit_members/",
          kalamela_admin_views.kalamela_admin_view_all_unit_members,
          name="kalamela_admin_view_all_unit_members"),
    
    path("kalamela_admin/kalamela_admin_edit_unit_members/<int:unit_member_id>/",
          kalamela_admin_views.kalamela_admin_edit_unit_members,
          name="kalamela_admin_edit_unit_members"),
    
    path('kalamela_admin/kalamela_admin_exclude_unit_member',
         kalamela_admin_views.kalamela_admin_exclude_unit_member,
         name='kalamela_admin_exclude_unit_member'),
    
    path('kalamela_admin/kalamela_admin_view_all_excluded_members',
         kalamela_admin_views.kalamela_admin_view_all_excluded_members,
         name='kalamela_admin_view_all_excluded_members'),
    

    path('kalamela_admin/individual_event/create/',
         kalamela_admin_views.kalamela_admin_add_individual_event,
         name='kalamela_admin_add_individual_event'),

    path('individual_event/update/<int:event_id>/',
         kalamela_admin_views.kalamela_admin_update_individual_event,
         name='kalamela_admin_update_individual_event'),

     path('kalamela_admin/group_event/create/',
         kalamela_admin_views.kalamela_admin_add_group_event,
         name='kalamela_admin_add_group_event'),
    
    path('group_event/update/<int:event_id>/',
         kalamela_admin_views.kalamela_admin_update_group_event,
         name='kalamela_admin_update_group_event'),
    
    path("kalamela_admin_view_individual_participants_list/",
         kalamela_admin_views.kalamela_admin_view_individual_participants_list,
         name="kalamela_admin_view_individual_participants_list"),
    
    path("kalamela_admin_view_group_participants_list/",
         kalamela_admin_views.kalamela_admin_view_group_participants_list,
         name="kalamela_admin_view_group_participants_list"),
    
    path("kalamela_edit_chest_number/",
         kalamela_admin_views.kalamela_edit_chest_number,
         name="kalamela_edit_chest_number"),
    
    path("kalamela_admin_view_events_preview/",
         kalamela_admin_views.kalamela_admin_view_events_preview,
         name="kalamela_admin_view_events_preview"),
    
    path("kalamela_admin_view_payments/",
         kalamela_admin_views.kalamela_admin_view_payments,
         name="kalamela_admin_view_payments"),
    
    path("kalamela_admin_invalid_payment_proof/",
         kalamela_admin_views.kalamela_admin_invalid_payment_proof,
         name="kalamela_admin_invalid_payment_proof"),
    
    path("kalamela_admin_approve_payment/",
         kalamela_admin_views.kalamela_admin_approve_payment,
         name="kalamela_admin_approve_payment"),
    
    path("kalamela_admin_export_all_events_data/",
         kalamela_admin_views.kalamela_admin_export_all_events_data,
         name="kalamela_admin_export_all_events_data"),
    
    path("admin_export_all_chest_numbers/",
         kalamela_admin_views.admin_export_all_chest_numbers,
         name="admin_export_all_chest_numbers"),
    
    path("kalamela_admin_individual_events_candidates/",
         kalamela_admin_views.kalamela_admin_individual_events_candidates,
         name="kalamela_admin_individual_events_candidates"),
    
    path("kalamela_admin_add_individual_events_score/",
         kalamela_admin_views.kalamela_admin_add_individual_events_score,
         name="kalamela_admin_add_individual_events_score"),
    
    path("kalamela_admin_view_events_score/",
         kalamela_admin_views.kalamela_admin_view_events_score,
         name="kalamela_admin_view_events_score"),
    
    path('kalamela_admin_view_appeals/',
         kalamela_admin_views.kalamela_admin_view_appeals,
         name='kalamela_admin_view_appeals'),
    
    path('kalamela_admin_view_appeals_action/',
         kalamela_admin_views.kalamela_admin_view_appeals_action,
         name='kalamela_admin_view_appeals_action'),
    
    path('kalamela_admin_view_update_individual_event_scorecard/',
         kalamela_admin_views.kalamela_admin_view_update_individual_event_scorecard,
         name='kalamela_admin_view_update_individual_event_scorecard'),
    
    path('kalamela_admin_save_updated_individual_scorecard/',
         kalamela_admin_views.kalamela_admin_save_updated_individual_scorecard,
         name='kalamela_admin_save_updated_individual_scorecard'),
    
    path("kalamela_admin_group_events_candidates/",
         kalamela_admin_views.kalamela_admin_group_events_candidates,
         name="kalamela_admin_group_events_candidates"),
    
    path("kalamela_admin_add_group_events_score/",
         kalamela_admin_views.kalamela_admin_add_group_events_score,
         name="kalamela_admin_add_group_events_score"),
    
    path("kalamela_admin_view_group_events_score/",
         kalamela_admin_views.kalamela_admin_view_group_events_score,
         name="kalamela_admin_view_group_events_score"),
    
    path("kalamela_admin_export_all_scores/",
         kalamela_admin_views.kalamela_admin_export_all_scores,
         name="kalamela_admin_export_all_scores"),
    
    path("kalamela_admin_unit_wise_results/",
         kalamela_admin_views.kalamela_admin_unit_wise_results,
         name="kalamela_admin_unit_wise_results"),
    
    path("kalamela_admin_district_wise_results/",
         kalamela_admin_views.kalamela_admin_district_wise_results,
         name="kalamela_admin_district_wise_results"),
    
    
    
    

    
    
    
    
    
    
  
    # kalamela_official_views urls
    path("kalamela_official_home_page/",
          kalamela_official_views.kalamela_official_home_page,
          name="kalamela_official_home_page"),

    path("kalamela_official_select_individual_event_participant/",
         kalamela_official_views.kalamela_official_select_individual_event_participant,
         name="kalamela_official_select_individual_event_participant"),

    path("kalamela_official_add_individual_event_participant/",
         kalamela_official_views.kalamela_official_add_individual_event_participant,
         name="kalamela_official_add_individual_event_participant"),

    path("kalamela_official_view_individual_participants_list/",
         kalamela_official_views.kalamela_official_view_individual_participants_list,
         name="kalamela_official_view_individual_participants_list"),
    
    path("kalamela_official_remove_individual_event_participant/",
         kalamela_official_views.kalamela_official_remove_individual_event_participant,
         name="kalamela_official_remove_individual_event_participant"),
    
#    Official Group events urls
    path("kalamela_official_select_group_event_participants/",
         kalamela_official_views.kalamela_official_select_group_event_participants,
         name="kalamela_official_select_group_event_participants"),

    path("kalamela_official_add_group_event_participant/",
         kalamela_official_views.kalamela_official_add_group_event_participant,
         name="kalamela_official_add_group_event_participant"),
    
    path("kalamela_official_view_group_participants_list/",
         kalamela_official_views.kalamela_official_view_group_participants_list,
         name="kalamela_official_view_group_participants_list"),
    
    path("kalamela_official_remove_group_event_participant/",
         kalamela_official_views.kalamela_official_remove_group_event_participant,
         name="kalamela_official_remove_group_event_participant"),
    
    path("kalamela_official_view_events_preview/",
         kalamela_official_views.kalamela_official_view_events_preview,
         name="kalamela_official_view_events_preview"),
    
    path("kalamela_official_make_payment/",
         kalamela_official_views.kalamela_official_make_payment,
         name="kalamela_official_make_payment"),
    
    path("kalamela_official_payment_proof_upload/",
         kalamela_official_views.kalamela_official_payment_proof_upload,
         name="kalamela_official_payment_proof_upload"),
    
    path("kalamela_official_print_form/",
         kalamela_official_views.kalamela_official_print_form,
         name="kalamela_official_print_form"),
    
    
    
    
    
]





