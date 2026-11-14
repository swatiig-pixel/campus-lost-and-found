from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from lostfound.models import Category, Item, Claim, Notification
from accounts.models import User


class Command(BaseCommand):
    help = 'Seeds initial campus categories, an admin user, sample students, and demo items.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Seeding database...'))

        # 1. Categories
        categories_data = [
            ('Electronics & Gadgets', 'Smartphones, laptops, calculators, chargers, headphones, pendrives.'),
            ('College IDs & Documents', 'College ID cards, library cards, driver licenses, project files, certificates.'),
            ('Keys & Keychains', 'Hostel keys, bike/car keys, locker keys.'),
            ('Bags & Backpacks', 'College bags, laptop sleeves, gym bags, pouches.'),
            ('Wallets & Purses', 'Wallets, coin purses, cardholders, money clips.'),
            ('Books & Stationery', 'Textbooks, lab manuals, notebooks, stationery pouches.'),
            ('Clothing & Accessories', 'Jackets, sweaters, caps, umbrellas, wristwatches, glasses.'),
            ('Sports & Fitness', 'Badminton rackets, footballs, water bottles, gym gear.'),
            ('Other / Miscellaneous', 'Items not fitting other specific campus categories.'),
        ]

        created_cats = {}
        for name, desc in categories_data:
            cat, created = Category.objects.get_or_create(name=name, defaults={'description': desc})
            created_cats[name] = cat
            if created:
                self.stdout.write(f'  Created Category: {name}')

        # 2. Admin User
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@campus.edu',
                'full_name': 'Campus Chief Proctor',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'department': 'Administration',
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('  Created superuser/admin: admin / admin123'))
        else:
            # Ensure admin has ADMIN role
            if admin_user.role != User.Role.ADMIN:
                admin_user.role = User.Role.ADMIN
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.save()

        # 3. Sample Students
        students_data = [
            ('student1', 'student1@campus.edu', 'Rahul Sharma', '1RV22CS085', 'Computer Science', 5, 'student123'),
            ('student2', 'student2@campus.edu', 'Priya Patel', '1RV22EC042', 'Electronics & Communication', 5, 'student123'),
            ('student3', 'student3@campus.edu', 'Ananya Iyer', '1RV23IS015', 'Information Science', 3, 'student123'),
        ]

        created_students = []
        for username, email, full_name, usn, dept, sem, pwd in students_data:
            stud, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'full_name': full_name,
                    'usn': usn,
                    'department': dept,
                    'semester': sem,
                    'role': User.Role.STUDENT,
                }
            )
            if created:
                stud.set_password(pwd)
                stud.save()
                self.stdout.write(f'  Created Student: {username} ({full_name}) / {pwd}')
            created_students.append(stud)

        # 4. Sample Lost & Found Items
        today = timezone.now().date()
        s1, s2, s3 = created_students[0], created_students[1], created_students[2]

        items_data = [
            {
                'user': s1,
                'category': created_cats['Electronics & Gadgets'],
                'name': 'Casio fx-991EX Scientific Calculator',
                'description': 'Black scientific calculator left on the 3rd bench in Room 204 after Mathematics internal test. Has a small green dot sticker on the back cover.',
                'report_type': Item.ReportType.LOST,
                'location': 'Academic Block B, Room 204',
                'report_date': today - timedelta(days=2),
                'verification_status': Item.VerificationStatus.APPROVED,
                'status': Item.Status.ACTIVE,
            },
            {
                'user': s2,
                'category': created_cats['College IDs & Documents'],
                'name': 'Campus Student ID Card in Blue Lanyard',
                'description': 'Student identity card found near the Cafeteria payment counter. Belonging to a 3rd semester student.',
                'report_type': Item.ReportType.FOUND,
                'location': 'Central Cafeteria Counter',
                'report_date': today - timedelta(days=1),
                'verification_status': Item.VerificationStatus.APPROVED,
                'status': Item.Status.ACTIVE,
            },
            {
                'user': s3,
                'category': created_cats['Keys & Keychains'],
                'name': 'Honda Activa Key with Iron Man Keychain',
                'description': 'Bike key found on the steps of the Central Library main entrance.',
                'report_type': Item.ReportType.FOUND,
                'location': 'Library Main Entrance Stairs',
                'report_date': today - timedelta(days=3),
                'verification_status': Item.VerificationStatus.APPROVED,
                'status': Item.Status.ACTIVE,
            },
            {
                'user': s1,
                'category': created_cats['Bags & Backpacks'],
                'name': 'Wildcraft Navy Blue Backpack',
                'description': 'Left in the basketball court seating area during evening practice. Contains data structures notes and a water bottle.',
                'report_type': Item.ReportType.LOST,
                'location': 'Sports Complex Basketball Court',
                'report_date': today - timedelta(days=4),
                'verification_status': Item.VerificationStatus.APPROVED,
                'status': Item.Status.ACTIVE,
            },
            {
                'user': s2,
                'category': created_cats['Electronics & Gadgets'],
                'name': 'Boat Airdopes 141 Charging Case (White)',
                'description': 'White wireless earbud case found on table 7 in the digital reading room.',
                'report_type': Item.ReportType.FOUND,
                'location': 'Central Library 1st Floor',
                'report_date': today,
                'verification_status': Item.VerificationStatus.PENDING,
                'status': Item.Status.ACTIVE,
            },
        ]

        for idata in items_data:
            item, created = Item.objects.get_or_create(
                name=idata['name'],
                user=idata['user'],
                defaults=idata
            )
            if created:
                self.stdout.write(f'  Created Demo Item: [{item.report_type}] {item.name}')

        self.stdout.write(self.style.SUCCESS('Successfully seeded database with categories, admin, students, and demo items!'))
