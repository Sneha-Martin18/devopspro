#!/usr/bin/env python3
"""
Script to create sample data for Assessment and Financial services
"""
import json
import uuid
from datetime import datetime, timedelta

import requests

# Service URLs
ASSESSMENT_URL = "http://localhost:8006/api/v1/assessments"
FINANCIAL_URL = "http://localhost:8007/api/v1/finances"


def create_sample_financial_data():
    """Create sample data for Financial Service"""
    print("Creating sample Financial Service data...")

    # Sample Fee Structure
    fee_structure = {
        "course_id": str(uuid.uuid4()),
        "fee_type": "tuition",
        "amount": "50000.00",
        "academic_year": "2024-25",
        "semester": "1",
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "is_active": True,
        "description": "Tuition fee for Computer Science - Semester 1",
    }

    try:
        response = requests.post(f"{FINANCIAL_URL}/fee-structures/", json=fee_structure)
        if response.status_code == 201:
            print("✓ Fee structure created successfully")
            fee_structure_id = response.json()["id"]
        else:
            print(f"✗ Failed to create fee structure: {response.status_code}")
            return
    except Exception as e:
        print(f"✗ Error creating fee structure: {e}")
        return

    # Sample Student Fee
    student_fee = {
        "student_id": str(uuid.uuid4()),
        "student_name": "John Doe",
        "student_email": "john.doe@example.com",
        "fee_structure": fee_structure_id,
        "amount_due": "50000.00",
        "amount_paid": "25000.00",
        "status": "partially_paid",
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
    }

    try:
        response = requests.post(f"{FINANCIAL_URL}/fees/", json=student_fee)
        if response.status_code == 201:
            print("✓ Student fee created successfully")
            student_fee_id = response.json()["id"]
        else:
            print(f"✗ Failed to create student fee: {response.status_code}")
            return
    except Exception as e:
        print(f"✗ Error creating student fee: {e}")
        return

    # Sample Payment
    payment = {
        "student_fee": student_fee_id,
        "amount": "25000.00",
        "payment_method": "online",
        "payment_date": datetime.now().isoformat(),
        "status": "completed",
        "gateway_transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "receipt_number": f"RCP_{uuid.uuid4().hex[:8]}",
    }

    try:
        response = requests.post(f"{FINANCIAL_URL}/payments/", json=payment)
        if response.status_code == 201:
            print("✓ Payment created successfully")
        else:
            print(f"✗ Failed to create payment: {response.status_code}")
    except Exception as e:
        print(f"✗ Error creating payment: {e}")

    # Sample Fine
    fine = {
        "student_id": str(uuid.uuid4()),
        "student_name": "Jane Smith",
        "student_email": "jane.smith@example.com",
        "fine_type": "library",
        "amount": "500.00",
        "reason": "Late return of library books",
        "issued_date": datetime.now().isoformat(),
        "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
        "status": "pending",
    }

    try:
        response = requests.post(f"{FINANCIAL_URL}/fines/", json=fine)
        if response.status_code == 201:
            print("✓ Fine created successfully")
        else:
            print(f"✗ Failed to create fine: {response.status_code}")
    except Exception as e:
        print(f"✗ Error creating fine: {e}")


def create_sample_assessment_data():
    """Create sample data for Assessment Service"""
    print("Creating sample Assessment Service data...")

    # Sample Assignment
    assignment = {
        "title": "Data Structures Assignment 1",
        "description": "Implement basic data structures: Stack, Queue, and Linked List",
        "course_id": str(uuid.uuid4()),
        "subject_id": str(uuid.uuid4()),
        "created_by": str(uuid.uuid4()),
        "max_marks": 100,
        "due_date": (datetime.now() + timedelta(days=14)).isoformat(),
        "academic_year": "2024-25",
        "semester": "1",
        "status": "published",
        "instructions": "Submit your code with proper documentation and test cases",
    }

    try:
        response = requests.post(f"{ASSESSMENT_URL}/assignments/", json=assignment)
        if response.status_code == 201:
            print("✓ Assignment created successfully")
            assignment_id = response.json()["id"]
        else:
            print(f"✗ Failed to create assignment: {response.status_code}")
            return
    except Exception as e:
        print(f"✗ Error creating assignment: {e}")
        return

    # Sample Submission
    submission = {
        "assignment": assignment_id,
        "student_id": str(uuid.uuid4()),
        "student_name": "Alice Johnson",
        "student_email": "alice.johnson@example.com",
        "submission_text": "Here is my implementation of the required data structures...",
        "submitted_at": datetime.now().isoformat(),
        "status": "submitted",
        "is_late": False,
    }

    try:
        response = requests.post(f"{ASSESSMENT_URL}/submissions/", json=submission)
        if response.status_code == 201:
            print("✓ Submission created successfully")
            submission_id = response.json()["id"]
        else:
            print(f"✗ Failed to create submission: {response.status_code}")
            return
    except Exception as e:
        print(f"✗ Error creating submission: {e}")
        return

    # Sample Exam
    exam = {
        "title": "Midterm Examination - Computer Science",
        "course_id": str(uuid.uuid4()),
        "subject_id": str(uuid.uuid4()),
        "exam_date": (datetime.now() + timedelta(days=21)).isoformat(),
        "duration_minutes": 180,
        "max_marks": 100,
        "academic_year": "2024-25",
        "semester": "1",
        "exam_type": "midterm",
        "status": "scheduled",
        "instructions": "Closed book examination. Calculators are allowed.",
    }

    try:
        response = requests.post(f"{ASSESSMENT_URL}/exams/", json=exam)
        if response.status_code == 201:
            print("✓ Exam created successfully")
        else:
            print(f"✗ Failed to create exam: {response.status_code}")
    except Exception as e:
        print(f"✗ Error creating exam: {e}")

    # Sample Grade Scale
    grade_scale = {
        "name": "Standard Grading Scale",
        "course_id": str(uuid.uuid4()),
        "scale_type": "percentage",
        "is_active": True,
        "grades": [
            {
                "grade": "A+",
                "min_percentage": 95.0,
                "max_percentage": 100.0,
                "gpa": 4.0,
            },
            {"grade": "A", "min_percentage": 90.0, "max_percentage": 94.9, "gpa": 4.0},
            {"grade": "B+", "min_percentage": 85.0, "max_percentage": 89.9, "gpa": 3.5},
            {"grade": "B", "min_percentage": 80.0, "max_percentage": 84.9, "gpa": 3.0},
            {"grade": "C", "min_percentage": 70.0, "max_percentage": 79.9, "gpa": 2.0},
            {"grade": "F", "min_percentage": 0.0, "max_percentage": 69.9, "gpa": 0.0},
        ],
    }

    try:
        response = requests.post(f"{ASSESSMENT_URL}/grade-scales/", json=grade_scale)
        if response.status_code == 201:
            print("✓ Grade scale created successfully")
        else:
            print(f"✗ Failed to create grade scale: {response.status_code}")
    except Exception as e:
        print(f"✗ Error creating grade scale: {e}")


def main():
    """Main function to create all sample data"""
    print("Creating sample data for Assessment and Financial services...")
    print("=" * 60)

    create_sample_financial_data()
    print()
    create_sample_assessment_data()

    print()
    print("=" * 60)
    print("Sample data creation completed!")
    print()
    print("You can now test the services:")
    print(f"- Financial Service API: http://localhost:8007/api/docs/")
    print(f"- Assessment Service API: http://localhost:8006/api/docs/")
    print(f"- API Gateway: http://localhost:8080/")


if __name__ == "__main__":
    main()
