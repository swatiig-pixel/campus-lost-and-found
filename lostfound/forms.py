from django import forms
from .models import Item, Claim, Message, Category
import datetime


class ReportItemForm(forms.ModelForm):
    report_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date',
                                      'max': datetime.date.today().isoformat()}),
        label='Date of Incident'
    )

    class Meta:
        model = Item
        fields = ['name', 'category', 'description', 'report_type', 'location', 'report_date', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Item name'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                  'placeholder': 'Describe the item in detail...'}),
            'report_type': forms.HiddenInput(),
            'location': forms.TextInput(attrs={'class': 'form-control',
                                               'placeholder': 'Where was it lost/found?'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if hasattr(image, 'content_type') and image.content_type not in allowed_types:
                raise forms.ValidationError('Only JPEG, PNG, GIF, and WebP images are allowed.')
            # Validate file size (5 MB)
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image size must be less than 5 MB.')
        return image


class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = ['description', 'identifying_details']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Describe why this item belongs to you...'
            }),
            'identifying_details': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Provide unique identifying details: serial number, contents, marks, color, brand, etc.'
            }),
        }
        labels = {
            'description': 'Claim Description',
            'identifying_details': 'Proof of Ownership',
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['message_text']
        widgets = {
            'message_text': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Type your message...'
            }),
        }
        labels = {'message_text': ''}


class ItemSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search items...'})
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    sort = forms.ChoiceField(
        required=False,
        choices=[('-created_at', 'Latest First'), ('created_at', 'Oldest First')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class AdminClaimReviewForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = ['status', 'admin_remarks']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'admin_remarks': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Add remarks (optional for approval, recommended for rejection)...'
            }),
        }


class AdminItemActionForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['verification_status', 'status']
        widgets = {
            'verification_status': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
