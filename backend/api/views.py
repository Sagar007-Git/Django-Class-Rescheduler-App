from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
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

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})
    else:
        return Response({'error': 'Invalid credentials'}, status=400)
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
    Teacher creates a request. 
    Prevents Duplicate Requests for the same slot.
    """
    try:
        requester = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return Response({"error": "You are not a registered teacher."}, status=400)

    data = request.data.copy()
    date_str = data.get('date')
    time_str = data.get('time_slot')

    # --- NEW: DUPLICATE CHECK ---
    existing_request = LeaveRequest.objects.filter(
        requester=requester,
        date=date_str,
        time_slot=time_str
    ).exists()

    if existing_request:
        return Response(
            {"error": "You have already requested a substitute for this class."}, 
            status=400
        )
    # -----------------------------
    
    # Create the Request
    leave_req = LeaveRequest.objects.create(
        requester=requester,
        date=date_str,
        time_slot=time_str,
        reason=data.get('reason', ''),
        status='PENDING_HOD'
    )

    # Create Proposals (Invites) for the selected teachers
    preferred_ids = data.get('preferred_teacher_ids', []) # List of IDs [2, 5, 8]
    for tid in preferred_ids:
        try:
            candidate = Teacher.objects.get(id=tid)
            SubstitutionProposal.objects.create(request=leave_req, candidate=candidate)
        except Teacher.DoesNotExist:
            continue # Skip invalid IDs

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

    # REJECTION LOGIC
    if action == 'REJECT':
        # We only mark it rejected if a proposal actually exists
        try:
            proposal = SubstitutionProposal.objects.get(request=leave_req, candidate=teacher)
            proposal.is_rejected = True
            proposal.save()
            return Response({"message": "You rejected the request."})
        except SubstitutionProposal.DoesNotExist:
            return Response({"message": "You were not invited, so no need to reject."}, status=200)

    # ACCEPTANCE LOGIC
    elif action == 'ACCEPT':
        try:
            with transaction.atomic():
                # LOCK the row so no one else can write to it
                locked_req = LeaveRequest.objects.select_for_update().get(id=request_id)
                
                # Check 1: Is it already taken?
                if locked_req.status == 'FILLED':
                    return Response({"error": "Too late! Another teacher accepted it."}, status=400)
                
                # Check 2: Is it approved by HOD?
                if locked_req.status != 'APPROVED_OPEN':
                    return Response({"error": "Request is not open for acceptance (Status is " + locked_req.status + ")"}, status=400)

                # Check 3: Prevent self-acceptance
                if locked_req.requester == teacher:
                    return Response({"error": "You cannot accept your own request!"}, status=400)

                # --- THE FIX: Auto-Create Proposal if missing ---
                # This allows any teacher to accept, even if not originally invited.
                proposal, created = SubstitutionProposal.objects.get_or_create(
                    request=locked_req, 
                    candidate=teacher
                )

                # Assign the substitute
                locked_req.status = 'FILLED'
                locked_req.final_substitute = teacher
                locked_req.save()
                
                # Mark proposal as accepted
                proposal.is_accepted = True
                proposal.save()

                return Response({"message": "Success! You are the substitute."})
                
        except Exception as e:
            return Response({"error": str(e)}, status=500)
    
    else:
        return Response({"error": "Invalid action. Use 'ACCEPT' or 'REJECT'."}, status=400)
    
# --- 5. HOD ACTIONS ---

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def hod_action(request, request_id):
    """
    HOD Approves/Rejects a request.
    (External SMS notifications have been removed for MVP)
    """
    try:
        req = LeaveRequest.objects.get(id=request_id)
        if not req.requester.is_hod: # Safety check
             pass 

        action = request.data.get('action') # "APPROVE" or "REJECT"

        if action == 'APPROVE':
            req.status = 'APPROVED_OPEN'
            req.save()
            return Response({"message": "Request Approved successfully."})

        elif action == 'REJECT':
            req.status = 'REJECTED'
            req.save()
            return Response({"message": "Request Rejected."})
            
        else:
            return Response({"error": "Invalid action"}, status=400)

    except LeaveRequest.DoesNotExist:
        return Response({"error": "Request not found"}, status=404)
    
# --- ADD THESE TO api/views.py ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_requests(request):
    """
    Teacher: View history of requests I have sent.
    """
    # Get requests where I am the requester
    my_requests = LeaveRequest.objects.filter(requester__user=request.user).order_by('-date')
    serializer = LeaveRequestSerializer(my_requests, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_hod_requests(request):
    """
    HOD: View ALL requests that need approval.
    """
    # Security Check: Is this user actually an HOD?
    if not request.user.teacher.is_hod:
        return Response({"error": "Authorized for HOD only"}, status=403)

    # Get all requests that are pending
    pending_requests = LeaveRequest.objects.filter(status='PENDING').order_by('date')
    serializer = LeaveRequestSerializer(pending_requests, many=True)
    return Response(serializer.data)