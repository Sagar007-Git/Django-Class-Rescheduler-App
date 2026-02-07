from django.shortcuts import get_object_or_404
from django.db import transaction, models
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from datetime import datetime
import json

from .models import Teacher, ClassSession, LeaveRequest, SubstitutionProposal, Subject
from .serializers import (TeacherSerializer, ClassSessionSerializer, 
                          LeaveRequestSerializer, UserSerializer)
from .firebase_utils import send_push_notification  # Import the utility

# --- 1. AUTHENTICATION & PROFILE ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    """
    Returns the logged-in user's profile and their Teacher ID.
    """
    try:
        teacher = Teacher.objects.get(user=request.user)
        serializer = TeacherSerializer(teacher)
        return Response(serializer.data)
    except Teacher.DoesNotExist:
        return Response({"error": "User is not linked to a Teacher profile"}, status=400)

# --- 2. SCHEDULE LOGIC ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_weekly_schedule(request):
    """
    Merges the Master Template (ClassSession) with Active Substitutions.
    This is what the teacher sees on their calendar.
    """
    teacher = Teacher.objects.get(user=request.user)
    
    # A. Get Static Schedule (Regular Classes)
    static_sessions = ClassSession.objects.filter(teacher=teacher)
    static_data = ClassSessionSerializer(static_sessions, many=True).data

    # B. Get Dynamic Schedule (Classes they are substituting for)
    # We only care about requests where they are the FINAL substitute
    sub_sessions = LeaveRequest.objects.filter(
        final_substitute=teacher,
        status='FILLED'
    )
    # Note: You might want a specific serializer for this, but for now we return raw data
    dynamic_data = LeaveRequestSerializer(sub_sessions, many=True).data

    return Response({
        "regular_schedule": static_data,
        "upcoming_substitutions": dynamic_data
    })

# --- 3. THE RECOMMENDATION ALGORITHM (Constraint Satisfaction) ---

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recommend_substitutes(request):
    """
    INPUT: { "date": "2024-02-12", "time_slot": "10:00:00", "subject_id": 1 }
    LOGIC: 
      1. Find teachers qualified for the subject.
      2. Exclude teachers busy in ClassSessions (Static).
      3. Exclude teachers busy in LeaveRequests (Dynamic).
      4. Sort by Workload (Greedy Load Balancing).
    """
    date_str = request.data.get('date')
    time_str = request.data.get('time_slot')
    subject_id = request.data.get('subject_id')

    # Convert date to Day of Week (0=Monday, 6=Sunday)
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    day_of_week = target_date.weekday() 
    
    # Step 1: Qualified Teachers
    subject = get_object_or_404(Subject, id=subject_id)
    candidates = Teacher.objects.filter(subjects=subject).exclude(user=request.user)

    # Step 2: Filter out Static Busy (Teaching a regular class)
    busy_static_ids = ClassSession.objects.filter(
        day=day_of_week, 
        start_time=time_str
    ).values_list('teacher_id', flat=True)

    # Step 3: Filter out Dynamic Busy (Already substituting elsewhere)
    busy_dynamic_ids = LeaveRequest.objects.filter(
        date=target_date,
        time_slot=time_str,
        status='FILLED'
    ).values_list('final_substitute_id', flat=True)

    # Combine exclusions
    final_candidates = candidates.exclude(id__in=busy_static_ids).exclude(id__in=busy_dynamic_ids)

    # Step 4: Greedy Load Balancing (Sort by Workload)
    # Annotate with count of classes (Static + Dynamic)
    ranked_candidates = final_candidates.annotate(
        static_load=Count('classsession'),
        dynamic_load=Count('substitutions_filled')
    ).annotate(
        total_load=models.F('static_load') + models.F('dynamic_load')
    ).order_by('total_load') # Ascending order (Least work first)

    return Response(TeacherSerializer(ranked_candidates, many=True).data)

# --- 4. REQUEST WORKFLOW ---

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_request(request):
    """
    Teacher creates a request. Status -> PENDING_HOD.
    """
    try:
        requester = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return Response({"error": "You are not a registered teacher."}, status=400)

    data = request.data.copy()
    
    # Create the Request
    leave_req = LeaveRequest.objects.create(
        requester=requester,
        date=data['date'],
        time_slot=data['time_slot'],
        reason=data['reason'],
        status='PENDING_HOD'
    )

    # Create Proposals (Invites) for the selected teachers
    preferred_ids = data.get('preferred_teacher_ids', []) # List of IDs [2, 5, 8]
    for tid in preferred_ids:
        candidate = Teacher.objects.get(id=tid)
        SubstitutionProposal.objects.create(request=leave_req, candidate=candidate)

    return Response({"message": "Request created. Waiting for HOD approval."}, status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def respond_to_request(request, request_id):
    """
    The SUBSTITUTE accepts or rejects.
    Uses OPTIMISTIC LOCKING to prevent race conditions.
    """
    action = request.data.get('action') # 'ACCEPT' or 'REJECT'
    teacher = Teacher.objects.get(user=request.user)
    leave_req = get_object_or_404(LeaveRequest, id=request_id)

    if action == 'REJECT':
        # Simple rejection logic
        proposal = SubstitutionProposal.objects.get(request=leave_req, candidate=teacher)
        proposal.is_rejected = True
        proposal.save()
        return Response({"message": "You rejected the request."})

    elif action == 'ACCEPT':
        try:
            with transaction.atomic():
                # LOCK the row so no one else can write to it
                locked_req = LeaveRequest.objects.select_for_update().get(id=request_id)
                
                if locked_req.status == 'FILLED':
                    return Response({"error": "Too late! Another teacher accepted it."}, status=400)
                
                if locked_req.status != 'APPROVED_OPEN':
                    return Response({"error": "Request is not open for acceptance."}, status=400)

                # Assign the substitute
                locked_req.status = 'FILLED'
                locked_req.final_substitute = teacher
                locked_req.save()
                
                # Mark proposal as accepted
                proposal = SubstitutionProposal.objects.get(request=leave_req, candidate=teacher)
                proposal.is_accepted = True
                proposal.save()

                return Response({"message": "Success! You are the substitute."})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

# --- 5. HOD ACTIONS ---

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def hod_action(request, request_id):
    """
    HOD Approves or Rejects a PENDING request.
    """
    # Security check: Ensure user is HOD
    try:
        hod = Teacher.objects.get(user=request.user)
        if not hod.is_hod:
            return Response({"error": "Unauthorized. HOD access required."}, status=403)
    except Teacher.DoesNotExist:
        return Response({"error": "User profile not found."}, status=400)

    action = request.data.get('action') # 'APPROVE' or 'REJECT'
    leave_req = get_object_or_404(LeaveRequest, id=request_id)

    if action == 'APPROVE':
        leave_req.status = 'APPROVED_OPEN'
        leave_req.save()
        
        # --- NEW NOTIFICATION LOGIC ---
        # 1. Find all candidates invited to this request
        proposals = SubstitutionProposal.objects.filter(request=leave_req)
        
        # 2. Collect their FCM Tokens (Phones)
        tokens = []
        for prop in proposals:
            if prop.candidate.fcm_token: # Only if they have a token saved
                tokens.append(prop.candidate.fcm_token)
        
        # 3. Send the Push Notification
        if tokens:
            send_push_notification(
                tokens=tokens,
                title="New Substitution Request",
                body=f"Request approved for {leave_req.date}. Can you accept?",
                data={"request_id": str(leave_req.id), "click_action": "FLUTTER_NOTIFICATION_CLICK"}
            )
        # -----------------------------

        return Response({"message": "Request Approved. Candidates notified."})
    
    elif action == 'REJECT':
        leave_req.status = 'REJECTED'
        leave_req.save()
        return Response({"message": "Request Rejected."})
    
    return Response({"error": "Invalid action"}, status=400)