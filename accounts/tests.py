from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User


class AccountsAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username='teststudent',
            password='password123',
            email='student@college.edu',
            full_name='Test Student',
            usn='1RV22CS999',
            department='Computer Science',
            semester=5,
            role=User.Role.STUDENT
        )
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            password='adminpassword',
            email='admin@college.edu',
            full_name='Test Admin',
            role=User.Role.ADMIN
        )

    def test_student_properties(self):
        self.assertTrue(self.student.is_student)
        self.assertFalse(self.student.is_admin_user)
        self.assertFalse(self.admin_user.is_student)
        self.assertTrue(self.admin_user.is_admin_user)

    def test_registration_success(self):
        url = reverse('accounts:register')
        data = {
            'username': 'newstudent',
            'full_name': 'New Student',
            'email': 'newstudent@college.edu',
            'usn': '1RV22CS888',
            'phone_number': '9876543210',
            'department': 'Information Science',
            'semester': '3',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('dashboard:student_dashboard'))
        self.assertTrue(User.objects.filter(username='newstudent').exists())
        user = User.objects.get(username='newstudent')
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertEqual(user.usn, '1RV22CS888')
        self.assertEqual(user.semester, 3)

    def test_registration_duplicate_usn_fails(self):
        url = reverse('accounts:register')
        data = {
            'username': 'anotherstudent',
            'full_name': 'Another Student',
            'email': 'another@college.edu',
            'usn': '1rv22cs999',  # case-insensitive duplicate of setUp USN
            'phone_number': '9876543210',
            'department': 'Mechanical Engineering',
            'semester': '4',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'usn', 'A student with this USN already exists.')

    def test_registration_duplicate_email_fails(self):
        url = reverse('accounts:register')
        data = {
            'username': 'diffuser',
            'full_name': 'Diff User',
            'email': 'student@college.edu',  # duplicate of setUp email
            'usn': '1RV22EC777',
            'department': 'Electrical Engineering',
            'semester': '2',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'email', 'An account with this email already exists.')

    def test_login_student_redirects_to_student_dashboard(self):
        url = reverse('accounts:login')
        response = self.client.post(url, {'username': 'teststudent', 'password': 'password123'})
        self.assertRedirects(response, reverse('dashboard:student_dashboard'))

    def test_login_admin_redirects_to_admin_dashboard(self):
        url = reverse('accounts:login')
        response = self.client.post(url, {'username': 'testadmin', 'password': 'adminpassword'})
        self.assertRedirects(response, reverse('dashboard:admin_dashboard'))

    def test_login_invalid_credentials_fails(self):
        url = reverse('accounts:login')
        response = self.client.post(url, {'username': 'teststudent', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')

    def test_login_deactivated_account_fails(self):
        self.student.is_active = False
        self.student.save()
        url = reverse('accounts:login')
        response = self.client.post(url, {'username': 'teststudent', 'password': 'password123'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This account has been deactivated')

    def test_logout(self):
        self.client.login(username='teststudent', password='password123')
        url = reverse('accounts:logout')
        response = self.client.post(url)
        self.assertRedirects(response, reverse('lostfound:landing'))

    def test_profile_view_and_update(self):
        self.client.login(username='teststudent', password='password123')
        url = reverse('accounts:profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Update profile
        update_data = {
            'full_name': 'Updated Student Name',
            'email': 'updated_email@college.edu',
            'phone_number': '9988776655',
            'department': 'Computer Science',
            'semester': 6,
        }
        post_response = self.client.post(url, update_data)
        self.assertRedirects(post_response, reverse('accounts:profile'))
        self.student.refresh_from_db()
        self.assertEqual(self.student.full_name, 'Updated Student Name')
        self.assertEqual(self.student.email, 'updated_email@college.edu')
        self.assertEqual(self.student.semester, 6)
