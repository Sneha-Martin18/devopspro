import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_management_system.settings')
django.setup()

from student_management_app.models import CustomUser, AdminHOD

def create_admin():
    try:
        # Create custom user
        user = CustomUser.objects.create_user(
            email="admin@gmail.com",
            password="admin@123",
            user_type=1,  # 1 for admin
            first_name="System",
            last_name="Admin"
        )
        
        # Create admin profile
        admin = AdminHOD.objects.create(
            admin=user
        )
        
        print("Admin user created successfully!")
        print("Email: admin@gmail.com")
        print("Password: admin@123")
        
    except Exception as e:
        print(f"Error creating admin: {str(e)}")

if __name__ == "__main__":
    create_admin()
