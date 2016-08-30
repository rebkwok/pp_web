# -*- coding: utf-8 -*-

from django import forms
from django.conf import settings


class EmailUsersForm(forms.Form):
    subject = forms.CharField(max_length=255, required=True,
                              widget=forms.TextInput(
                                  attrs={'class': 'form-control'}))
    from_address = forms.EmailField(max_length=255,
                                    initial=settings.DEFAULT_STUDIO_EMAIL,
                                    required=True,
                                    widget=forms.TextInput(
                                        attrs={'class': 'form-control'}),
                                    help_text='This will be the reply-to address')
    cc = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
                'class': "regular-checkbox ppadmin-list",
                'id': 'cc_id'
            }),
        label="cc. from address",
        initial=True,
        required=False
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control email-message',
                                     'rows': 10}),
        required=True)
