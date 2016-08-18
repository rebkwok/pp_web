from django.core.exceptions import ValidationError


def validate_confirm(value):
    if not value:
        raise ValidationError(
            'You must confirm that you accept the disclaimer terms'
        )


def validate_age(value):
    if not value:
        raise ValidationError(
            'You must confirm that you are 18 or over'
        )


def validate_medical_treatment_permission(value):
    if not value:
        raise ValidationError(
            'You must confirm that you give permission for medical treatment '
            'in the event of an accident'
        )
