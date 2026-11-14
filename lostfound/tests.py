from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from lostfound.models import Category, Item, Claim, Message, Notification, ItemStatusHistory
from lostfound import services


class LostFoundComprehensiveTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.student1 = User.objects.create_user(
            username='student1', password='password123',
            email='student1@college.edu', full_name='Alice Student',
            usn='1RV22CS001', role=User.Role.STUDENT
        )
        self.student2 = User.objects.create_user(
            username='student2', password='password123',
            email='student2@college.edu', full_name='Bob Student',
            usn='1RV22EC002', role=User.Role.STUDENT
        )
        self.student3 = User.objects.create_user(
            username='student3', password='password123',
            email='student3@college.edu', full_name='Charlie Student',
            usn='1RV22ME003', role=User.Role.STUDENT
        )
        self.admin_user = User.objects.create_superuser(
            username='adminuser', password='adminpassword',
            email='admin@college.edu', full_name='Proctor Admin',
            role=User.Role.ADMIN
        )

        # Categories
        self.cat_electronics = Category.objects.create(name='Electronics & Gadgets')
        self.cat_keys = Category.objects.create(name='Keys & Keychains')

        # Existing Approved Found Item reported by student1
        self.found_item = Item.objects.create(
            user=self.student1,
            category=self.cat_electronics,
            name='Sony WH-1000XM4 Headphones',
            description='Black over-ear headphones found in Library reading room.',
            report_type=Item.ReportType.FOUND,
            location='Library 2nd Floor',
            report_date=timezone.now().date(),
            verification_status=Item.VerificationStatus.APPROVED,
            status=Item.Status.ACTIVE,
        )

    # ── Item Reporting & Visibility ──────────────────────────────

    def test_report_lost_item_creates_pending_record(self):
        self.client.login(username='student1', password='password123')
        url = reverse('lostfound:report_lost')
        data = {
            'name': 'Titan Blue Dial Watch',
            'category': self.cat_electronics.pk,
            'description': 'Silver strap wrist watch left in computer lab 3.',
            'report_type': 'LOST',
            'location': 'CS Lab 3',
            'report_date': timezone.now().date().isoformat(),
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        item = Item.objects.get(name='Titan Blue Dial Watch')
        self.assertEqual(item.report_type, Item.ReportType.LOST)
        self.assertEqual(item.verification_status, Item.VerificationStatus.PENDING)
        self.assertEqual(item.status, Item.Status.ACTIVE)
        self.assertEqual(item.user, self.student1)

    def test_public_listings_only_show_approved_items(self):
        # Create a pending lost item
        pending_item = Item.objects.create(
            user=self.student1,
            category=self.cat_electronics,
            name='Pending Laptop Charger',
            description='Black 65W charger',
            report_type=Item.ReportType.LOST,
            location='Audi 2',
            report_date=timezone.now().date(),
            verification_status=Item.VerificationStatus.PENDING,
        )

        self.client.login(username='student2', password='password123')
        # View lost items listing
        response = self.client.get(reverse('lostfound:lost_items'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Pending Laptop Charger')

        # Approve the item via service
        services.approve_item(pending_item, self.admin_user)
        response2 = self.client.get(reverse('lostfound:lost_items'))
        self.assertContains(response2, 'Pending Laptop Charger')

    def test_unapproved_item_detail_forbidden_for_other_students(self):
        unapproved = Item.objects.create(
            user=self.student1,
            category=self.cat_keys,
            name='Secret Brass Key',
            description='Dorm room key',
            report_type=Item.ReportType.LOST,
            location='Hostel Block',
            report_date=timezone.now().date(),
            verification_status=Item.VerificationStatus.PENDING,
        )
        # Owner can view
        self.client.login(username='student1', password='password123')
        resp_owner = self.client.get(reverse('lostfound:item_detail', args=[unapproved.pk]))
        self.assertEqual(resp_owner.status_code, 200)

        # Another student gets 404
        self.client.login(username='student2', password='password123')
        resp_other = self.client.get(reverse('lostfound:item_detail', args=[unapproved.pk]))
        self.assertEqual(resp_other.status_code, 404)

        # Admin can view
        self.client.login(username='adminuser', password='adminpassword')
        resp_admin = self.client.get(reverse('lostfound:item_detail', args=[unapproved.pk]))
        self.assertEqual(resp_admin.status_code, 200)

    # ── Search & Filter ──────────────────────────────────────────

    def test_search_by_keyword_and_category(self):
        self.client.login(username='student2', password='password123')
        url = reverse('lostfound:found_items')
        
        # Search by keyword
        resp_match = self.client.get(url, {'q': 'Headphones'})
        self.assertContains(resp_match, 'Sony WH-1000XM4')

        resp_nomatch = self.client.get(url, {'q': 'Umbrella'})
        self.assertNotContains(resp_nomatch, 'Sony WH-1000XM4')

        # Filter by matching category
        resp_cat = self.client.get(url, {'category': self.cat_electronics.pk})
        self.assertContains(resp_cat, 'Sony WH-1000XM4')

        # Filter by non-matching category
        resp_cat_diff = self.client.get(url, {'category': self.cat_keys.pk})
        self.assertNotContains(resp_cat_diff, 'Sony WH-1000XM4')

    # ── Claims Workflow & Concurrency ─────────────────────────────

    def test_student_cannot_claim_own_item(self):
        # student1 reported found_item; student1 cannot claim it
        self.client.login(username='student1', password='password123')
        url = reverse('lostfound:submit_claim', args=[self.found_item.pk])
        response = self.client.get(url)
        self.assertRedirects(response, reverse('lostfound:item_detail', args=[self.found_item.pk]))

    def test_student_can_submit_claim_with_proof(self):
        self.client.login(username='student2', password='password123')
        url = reverse('lostfound:submit_claim', args=[self.found_item.pk])
        claim_data = {
            'description': 'I left my Sony headphones on table 4.',
            'identifying_details': 'Serial # SN99281, small scratch on right ear cup, custom decal on case.',
        }
        response = self.client.post(url, claim_data)
        self.assertRedirects(response, reverse('lostfound:my_claims'))
        self.assertTrue(Claim.objects.filter(item=self.found_item, claimant=self.student2).exists())
        claim = Claim.objects.get(item=self.found_item, claimant=self.student2)
        self.assertEqual(claim.status, Claim.Status.PENDING)

        # Reporter (student1) receives notification
        self.assertTrue(Notification.objects.filter(
            user=self.student1,
            notification_type=Notification.NotificationType.CLAIM_SUBMITTED
        ).exists())

    def test_duplicate_pending_claim_prevented(self):
        self.client.login(username='student2', password='password123')
        Claim.objects.create(
            item=self.found_item,
            claimant=self.student2,
            description='First claim',
            identifying_details='Serial 123',
            status=Claim.Status.PENDING
        )
        url = reverse('lostfound:submit_claim', args=[self.found_item.pk])
        response = self.client.post(url, {
            'description': 'Duplicate claim attempt',
            'identifying_details': 'Serial 123',
        })
        self.assertRedirects(response, reverse('lostfound:my_claims'))
        # Ensure only 1 claim exists
        self.assertEqual(Claim.objects.filter(item=self.found_item, claimant=self.student2).count(), 1)

    def test_admin_approve_claim_rejects_competing_claims(self):
        # Two students submit claims for the same item
        claim2 = Claim.objects.create(
            item=self.found_item,
            claimant=self.student2,
            description='Claim by Bob',
            identifying_details='Has scratch',
            status=Claim.Status.PENDING
        )
        claim3 = Claim.objects.create(
            item=self.found_item,
            claimant=self.student3,
            description='Claim by Charlie',
            identifying_details='Serial 456',
            status=Claim.Status.PENDING
        )

        # Admin approves claim2
        success, msg = services.approve_claim(claim2, self.admin_user)
        self.assertTrue(success)

        claim2.refresh_from_db()
        claim3.refresh_from_db()
        self.found_item.refresh_from_db()

        # claim2 is approved
        self.assertEqual(claim2.status, Claim.Status.APPROVED)
        # claim3 was automatically rejected
        self.assertEqual(claim3.status, Claim.Status.REJECTED)
        # item status is CLAIMED
        self.assertEqual(self.found_item.status, Item.Status.CLAIMED)

        # Notifications sent
        self.assertTrue(Notification.objects.filter(
            user=self.student2,
            notification_type=Notification.NotificationType.CLAIM_APPROVED
        ).exists())
        self.assertTrue(Notification.objects.filter(
            user=self.student3,
            notification_type=Notification.NotificationType.CLAIM_REJECTED
        ).exists())

    def test_mark_item_returned(self):
        services.approve_claim(
            Claim.objects.create(
                item=self.found_item, claimant=self.student2,
                description='My headphones', identifying_details='S/N 1',
                status=Claim.Status.PENDING
            ),
            self.admin_user
        )
        # Admin marks returned
        services.mark_item_returned(self.found_item, self.admin_user, remarks='Handover complete at Proctor Office.')
        self.found_item.refresh_from_db()
        self.assertEqual(self.found_item.status, Item.Status.RETURNED)

        # History record created
        self.assertTrue(ItemStatusHistory.objects.filter(
            item=self.found_item, new_status=Item.Status.RETURNED
        ).exists())

    # ── Authorization & Access Control ────────────────────────────

    def test_student_cannot_access_admin_dashboard(self):
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertRedirects(response, reverse('dashboard:student_dashboard'))

    def test_student_cannot_access_admin_items(self):
        self.client.login(username='student1', password='password123')
        response = self.client.get(reverse('lostfound:admin_items'))
        self.assertRedirects(response, reverse('dashboard:student_dashboard'))

    def test_unauthenticated_redirected_to_login(self):
        response = self.client.get(reverse('dashboard:student_dashboard'))
        self.assertRedirects(response, f"/accounts/login/?next={reverse('dashboard:student_dashboard')}")

    # ── Private Handover Messaging ────────────────────────────────

    def test_messaging_between_finder_and_approved_claimant(self):
        claim = Claim.objects.create(
            item=self.found_item, claimant=self.student2,
            description='My headphones', identifying_details='Proof',
            status=Claim.Status.PENDING
        )
        services.approve_claim(claim, self.admin_user)

        # Claimant sends message to finder (student1)
        self.client.login(username='student2', password='password123')
        url = reverse('lostfound:message_conversation', args=[self.found_item.pk, self.student1.pk])
        post_resp = self.client.post(url, {'message_text': 'Hi, can we meet at the library tomorrow at 3 PM?'})
        self.assertRedirects(post_resp, url)

        msg = Message.objects.filter(item=self.found_item, sender=self.student2, receiver=self.student1).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.message_text, 'Hi, can we meet at the library tomorrow at 3 PM?')

        # Third party student cannot access the conversation
        self.client.login(username='student3', password='password123')
        forbidden_resp = self.client.get(url)
        self.assertRedirects(forbidden_resp, reverse('lostfound:messages_inbox'))
