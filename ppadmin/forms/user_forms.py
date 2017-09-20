# -*- coding: utf-8 -*-

from django import forms


class UserListSearchForm(forms.Form):
    search = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Search first, last and username',
                'style': 'width: 250px;'
            }
        ),
        required=False
    )
