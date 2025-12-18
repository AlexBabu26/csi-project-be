from django.db import models
from auth_app.models import (UnitMembers,
                             CustomUser)

# Create your models here.

class IndividualEvent(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=200,
                                null=True)
    description = models.TextField(max_length=200)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"

class GroupEvent(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(max_length=200)
    max_allowed_limit = models.IntegerField(null=True)
    min_allowed_limit = models.IntegerField(null=True)
    per_unit_allowed_limit = models.IntegerField(default=2)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} : {self.max_allowed_limit}"

class IndividualEventParticipation(models.Model):
    individual_event = models.ForeignKey(IndividualEvent,
                                         on_delete=models.DO_NOTHING)
    participant = models.ForeignKey(UnitMembers,
                                    on_delete=models.CASCADE)
    added_by = models.ForeignKey(CustomUser,
                                 on_delete=models.DO_NOTHING)
    chest_number = models.CharField(max_length=200, null=True)
    seniority_category = models.CharField(max_length=200)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.participant.name} : {self.individual_event.name} : {self.chest_number}"


class GroupEventParticipation(models.Model):
    group_event = models.ForeignKey(GroupEvent,
                                    on_delete=models.DO_NOTHING)
    participant = models.ForeignKey(UnitMembers,
                                    on_delete=models.DO_NOTHING)
    chest_number = models.TextField(max_length=200)
    added_by = models.ForeignKey(CustomUser,
                                 on_delete=models.DO_NOTHING)

    def __str__(self):
        return f"{self.participant.name} : {self.group_event.name} : {self.chest_number}"


class KalamelaExcludeMembers(models.Model):
    members = models.ForeignKey(UnitMembers,
                                on_delete=models.DO_NOTHING)

    def __str__(self):
        return f"Excluded from event: {self.members.name}"


class KalamelaPayements(models.Model):
    paid_by = models.ForeignKey(CustomUser,
                                on_delete=models.DO_NOTHING)
    individual_events_count = models.IntegerField(null=True)
    group_events_count = models.IntegerField(null=True)
    total_amount_to_pay = models.DecimalField(max_digits=8, decimal_places=2)
    payment_proof =  models.ImageField(upload_to='uploads/Kalamela Payments/', null=True)
    payment_status = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.paid_by_clegy_district__name} : {self.total_amount_to_pay}"


class IndividualEventScoreCard(models.Model):
    event_participation=models.ForeignKey(IndividualEventParticipation,
                                          on_delete=models.DO_NOTHING)
    participant=models.ForeignKey(UnitMembers,
                                     on_delete=models.DO_NOTHING,
                                     null=True)
    awarded_mark = models.IntegerField(null=True)
    grade=models.CharField(max_length=200,
                           null=True)
    total_points=models.IntegerField(null=True)
    added_on = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.event_participation.individual_event.name}"


class GroupEventScoreCard(models.Model):
    event_name = models.CharField(max_length=200,
                           null=True)
    awarded_mark = models.IntegerField(null=True)
    chest_number=models.CharField(max_length=200,
                           null=True)
    grade=models.CharField(max_length=200,
                           null=True)
    total_points=models.IntegerField(null=True)
    added_on = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{event_participation.group_event.name}:{event_participation.group_event.participant.name}:{event_participation.group_event.participant.registered_user.unit_name.name}"


class Appeal(models.Model):
    added_by = models.ForeignKey(UnitMembers,
                                on_delete=models.CASCADE)
    chest_number = models.CharField(max_length=200)
    event_name = models.CharField(max_length=200, null=True)
    statement = models.TextField()
    reply = models.TextField(null=True)
    status = models.CharField(max_length=200)
    created_on = models.DateTimeField(auto_now_add=True)


class AppealPayements(models.Model):
    appeal = models.ForeignKey(Appeal,
                               on_delete=models.DO_NOTHING,
                               null=True)
    total_amount_to_pay = models.DecimalField(max_digits=8, decimal_places=2)
    payment_type = models.CharField(max_length=100, null=True)
    payment_status = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.paid_by_clegy_district__name} : {self.total_amount_to_pay}"
