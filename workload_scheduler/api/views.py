"""
Views for the Dynamic Teaching Workload Scheduler API.
"""
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    User, Department, Teacher, Subject, TeacherSubject,
    ClassSession, LeaveRequest, SubstitutionProposal
)
from .serializers import (
    UserSerializer, DepartmentSerializer, TeacherSerializer,
    SubjectSerializer, TeacherSubjectSerializer, ClassSessionSerializer,
    LeaveRequestSerializer, SubstitutionProposalSerializer,
    WeeklyScheduleSerializer, CreateLeaveRequestSerializer,
    SubstituteRecommendationSerializer, ProposalResponseSerializer
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain view with user data in response."""
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Get user data
            username = request.data.get('username')
            try:
                user = User.objects.get(username=username)
                user_data = UserSerializer(user).data
                response.data.update({
                    'user': user_data,
                    'teacher_id': None
                })
                
                # Add teacher ID if user is a teacher
                if user.is_teacher:
                    try:
                        teacher = Teacher.objects.get(user=user)
                        response.data['teacher_id'] = teacher.id
                    except Teacher.DoesNotExist:
                        pass
            except User.DoesNotExist:
                pass
        
        return response


class DepartmentViewSet(viewsets.ModelViewSet):
    """API endpoint for Department CRUD operations."""
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Only HODs can modify departments."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            from rest_framework.permissions import IsAdminUser
            return [IsAdminUser()]
        return super().get_permissions()


class TeacherViewSet(viewsets.ModelViewSet):
    """API endpoint for Teacher CRUD operations."""
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter teachers by department for non-HOD users."""
        user = self.request.user
        
        if user.is_hod:
            # HOD can see all teachers in their department
            try:
                hod_teacher = Teacher.objects.get(user=user)
                return self.queryset.filter(department=hod_teacher.department)
            except Teacher.DoesNotExist:
                return self.queryset.none()
        elif user.is_teacher:
            # Teachers can see all teachers in their department
            try:
                teacher = Teacher.objects.get(user=user)
                return self.queryset.filter(department=teacher.department)
            except Teacher.DoesNotExist:
                return self.queryset.none()
        else:
            # Admins can see all
            return self.queryset
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current teacher's profile."""
        try:
            teacher = Teacher.objects.get(user=request.user)
            serializer = self.get_serializer(teacher)
            return Response(serializer.data)
        except Teacher.DoesNotExist:
            return Response(
                {'error': 'Teacher profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )


class SubjectViewSet(viewsets.ModelViewSet):
    """API endpoint for Subject CRUD operations."""
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter subjects by department."""
        user = self.request.user
        
        if user.is_teacher:
            try:
                teacher = Teacher.objects.get(user=user)
                return self.queryset.filter(department=teacher.department)
            except Teacher.DoesNotExist:
                return self.queryset.none()
        elif user.is_hod:
            try:
                hod_teacher = Teacher.objects.get(user=user)
                return self.queryset.filter(department=hod_teacher.department)
            except Teacher.DoesNotExist:
                return self.queryset.none()
        else:
            return self.queryset


class TeacherSubjectViewSet(viewsets.ModelViewSet):
    """API endpoint for Teacher-Subject qualification CRUD operations."""
    queryset = TeacherSubject.objects.all()
    serializer_class = TeacherSubjectSerializer
    permission_classes = [IsAuthenticated]


class ClassSessionViewSet(viewsets.ModelViewSet):
    """API endpoint for ClassSession CRUD operations."""
    queryset = ClassSession.objects.all()
    serializer_class = ClassSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter class sessions based on user role."""
        user = self.request.user
        
        if user.is_teacher:
            try:
                teacher = Teacher.objects.get(user=user)
                # Get sessions where teacher is assigned
                return self.queryset.filter(assigned_teacher=teacher)
            except Teacher.DoesNotExist:
                return self.queryset.none()
        elif user.is_hod:
            try:
                hod_teacher = Teacher.objects.get(user=user)
                # Get all sessions in HOD's department
                return self.queryset.filter(
                    subject__department=hod_teacher.department
                )
            except Teacher.DoesNotExist:
                return self.queryset.none()
        else:
            return self.queryset


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """API endpoint for LeaveRequest CRUD operations."""
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter leave requests based on user role."""
        user = self.request.user
        
        if user.is_teacher:
            try:
                teacher = Teacher.objects.get(user=user)
                # Teachers can see their own leave requests
                return self.queryset.filter(requester=teacher)
            except Teacher.DoesNotExist:
                return self.queryset.none()
        elif user.is_hod:
            try:
                hod_teacher = Teacher.objects.get(user=user)
                # HOD can see leave requests from teachers in their department
                return self.queryset.filter(
                    requester__department=hod_teacher.department
                )
            except Teacher.DoesNotExist:
                return self.queryset.none()
        else:
            return self.queryset
    
    def perform_create(self, serializer):
        """Set the requester to current teacher."""
        teacher = Teacher.objects.get(user=self.request.user)
        serializer.save(requester=teacher)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """HOD approves a leave request."""
        try:
            leave_request = self.get_object()
            user = request.user
            
            # Check if user is HOD
            if not user.is_hod:
                return Response(
                    {'error': 'Only HOD can approve leave requests.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if request is in pending state
            if leave_request.status != LeaveRequest.Status.PENDING_HOD:
                return Response(
                    {'error': f'Leave request is not pending approval. Current status: {leave_request.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update status
            leave_request.status = LeaveRequest.Status.APPROVED_OPEN
            leave_request.save()
            
            # Send notifications to proposed teachers
            proposals = leave_request.substitution_proposals.filter(
                status=SubstitutionProposal.Status.QUEUED
            )
            for proposal in proposals:
                proposal.status = SubstitutionProposal.Status.SENT
                proposal.sent_at = timezone.now()
                proposal.save()
                
                # Send FCM notification (stub)
                self._send_fcm_notification(
                    proposal.proposed_teacher.fcm_token,
                    title='Substitution Request',
                    body=f'You have been requested to substitute for {leave_request.requester.full_name}'
                )
            
            serializer = self.get_serializer(leave_request)
            return Response(serializer.data)
            
        except LeaveRequest.DoesNotExist:
            return Response(
                {'error': 'Leave request not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a leave request (only requester or HOD)."""
        try:
            leave_request = self.get_object()
            user = request.user
            
            # Check permissions
            is_requester = leave_request.requester.user == user
            is_hod = user.is_hod
            
            if not (is_requester or is_hod):
                return Response(
                    {'error': 'Only requester or HOD can cancel leave requests.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if request can be cancelled
            if leave_request.status == LeaveRequest.Status.FILLED:
                return Response(
                    {'error': 'Cannot cancel a filled leave request.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update status
            leave_request.status = LeaveRequest.Status.CANCELLED
            leave_request.save()
            
            # Auto-cancel all pending proposals
            proposals = leave_request.substitution_proposals.filter(
                status__in=[SubstitutionProposal.Status.QUEUED, SubstitutionProposal.Status.SENT]
            )
            for proposal in proposals:
                proposal.status = SubstitutionProposal.Status.AUTO_CANCELLED
                proposal.save()
            
            serializer = self.get_serializer(leave_request)
            return Response(serializer.data)
            
        except LeaveRequest.DoesNotExist:
            return Response(
                {'error': 'Leave request not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def _send_fcm_notification(self, token, title, body):
        """Stub for FCM notification sending."""
        # In production, implement Firebase Cloud Messaging
        # For now, just log
        print(f"[FCM Notification] To: {token}, Title: {title}, Body: {body}")


class SubstitutionProposalViewSet(viewsets.ModelViewSet):
    """API endpoint for SubstitutionProposal operations."""
    queryset = SubstitutionProposal.objects.all()
    serializer_class = SubstitutionProposalSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter proposals based on user role."""
        user = self.request.user
        
        if user.is_teacher:
            try:
                teacher = Teacher.objects.get(user=user)
                # Teachers can see proposals sent to them
                return self.queryset.filter(proposed_teacher=teacher)
            except Teacher.DoesNotExist:
                return self.queryset.none()
        else:
            # HODs and admins can see all proposals
            return self.queryset
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Teacher responds to a substitution proposal."""
        try:
            proposal = self.get_object()
            serializer = ProposalResponseSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            action = serializer.validated_data['action']
            user = request.user
            
            # Verify the responding user is the proposed teacher
            if proposal.proposed_teacher.user != user:
                return Response(
                    {'error': 'You are not authorized to respond to this proposal.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Use database transaction with row locking
            with transaction.atomic():
                # Lock the related leave request
                leave_request = LeaveRequest.objects.select_for_update().get(
                    id=proposal.request.id
                )
                
                if action == 'ACCEPT':
                    return self._handle_accept_action(proposal, leave_request)
                elif action == 'REJECT':
                    return self._handle_reject_action(proposal, leave_request)
                else:
                    return Response(
                        {'error': 'Invalid action.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
        except SubstitutionProposal.DoesNotExist:
            return Response(
                {'error': 'Proposal not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except LeaveRequest.DoesNotExist:
            return Response(
                {'error': 'Related leave request not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def _handle_accept_action(self, proposal, leave_request):
        """Handle ACCEPT action for proposal."""
        # Verify leave request is still open for substitution
        if leave_request.status != LeaveRequest.Status.APPROVED_OPEN:
            return Response(
                {'error': f'Leave request is not open for substitution. Current status: {leave_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update proposal status
        proposal.status = SubstitutionProposal.Status.ACCEPTED
        proposal.responded_at = timezone.now()
        proposal.save()
        
        # Update leave request
        leave_request.status = LeaveRequest.Status.FILLED
        leave_request.final_substitute = proposal.proposed_teacher
        leave_request.save()
        
        # Auto-cancel all other proposals for this request
        other_proposals = leave_request.substitution_proposals.filter(
            ~Q(id=proposal.id),
            status__in=[SubstitutionProposal.Status.QUEUED, SubstitutionProposal.Status.SENT]
        )
        for other_proposal in other_proposals:
            other_proposal.status = SubstitutionProposal.Status.AUTO_CANCELLED
            other_proposal.save()
        
        # Notify requester
        self._send_fcm_notification(
            leave_request.requester.fcm_token,
            title='Substitution Accepted',
            body=f'{proposal.proposed_teacher.full_name} has accepted your substitution request.'
        )
        
        serializer = self.get_serializer(proposal)
        return Response(serializer.data)
    
    def _handle_reject_action(self, proposal, leave_request):
        """Handle REJECT action for proposal."""
        # Update proposal status
        proposal.status = SubstitutionProposal.Status.REJECTED
        proposal.responded_at = timezone.now()
        proposal.save()
        
        serializer = self.get_serializer(proposal)
        return Response(serializer.data)
    
    def _send_fcm_notification(self, token, title, body):
        """Stub for FCM notification sending."""
        print(f"[FCM Notification] To: {token}, Title: {title}, Body: {body}")


class WeeklyScheduleView(APIView):
    """
    API endpoint to show teacher's weekly schedule.
    GET /api/schedule/my-weekly/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get current teacher's schedule for the current week,
        adjusting for substitutions.
        """
        # Get current teacher
        try:
            teacher = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            return Response(
                {'error': 'Teacher profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get start and end dates of current week (Monday to Sunday)
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        end_of_week = start_of_week + timedelta(days=6)  # Sunday
        
        # Initialize result list
        schedule = []
        
        # Step 1: Get regular sessions (teacher's assigned classes)
        regular_sessions = ClassSession.objects.filter(
            assigned_teacher=teacher
        )
        
        # For each day in the week
        current_date = start_of_week
        while current_date <= end_of_week:
            day_of_week = current_date.weekday()  # Monday=0
            
            # Get sessions for this day
            day_sessions = regular_sessions.filter(day_of_week=day_of_week)
            
            for session in day_sessions:
                # Step 2: Check if session is cancelled due to filled leave request
                is_cancelled = LeaveRequest.objects.filter(
                    requester=teacher,
                    class_session=session,
                    date_of_leave=current_date,
                    status=LeaveRequest.Status.FILLED
                ).exists()
                
                if not is_cancelled:
                    # Add regular session
                    schedule.append({
                        'id': session.id,
                        'date': current_date,
                        'subject': session.subject,
                        'assigned_teacher': session.assigned_teacher,
                        'day_of_week': session.day_of_week,
                        'start_time': session.start_time,
                        'end_time': session.end_time,
                        'semester': session.semester,
                        'section': session.section,
                        'is_substitution': False,
                        'substitution_details': None
                    })
            
            current_date += timedelta(days=1)
        
        # Step 3: Add substitution sessions where teacher is the substitute
        substitution_requests = LeaveRequest.objects.filter(
            final_substitute=teacher,
            date_of_leave__range=[start_of_week, end_of_week],
            status=LeaveRequest.Status.FILLED
        )
        
        for leave_request in substitution_requests:
            session = leave_request.class_session
            
            schedule.append({
                'id': session.id,
                'date': leave_request.date_of_leave,
                'subject': session.subject,
                'assigned_teacher': teacher,  # Teacher is the substitute
                'day_of_week': session.day_of_week,
                'start_time': session.start_time,
                'end_time': session.end_time,
                'semester': session.semester,
                'section': session.section,
                'is_substitution': True,
                'substitution_details': {
                    'original_teacher': leave_request.requester.full_name,
                    'leave_reason': leave_request.reason,
                    'request_id': leave_request.id
                }
            })
        
        # Sort schedule by date and time
        schedule.sort(key=lambda x: (x['date'], x['start_time']))
        
        # Serialize and return
        serializer = WeeklyScheduleSerializer(schedule, many=True)
        return Response(serializer.data)


class SubstituteRecommendationView(APIView):
    """
    API endpoint to recommend substitute teachers.
    GET /api/substitutes/recommend/?class_session_id=X&date=YYYY-MM-DD
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Recommend qualified, available, and least-burdened colleagues.
        """
        class_session_id = request.query_params.get('class_session_id')
        date_str = request.query_params.get('date')
        
        if not class_session_id or not date_str:
            return Response(
                {'error': 'Both class_session_id and date parameters are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Parse date
            date_of_leave = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Get class session
            class_session = ClassSession.objects.get(id=class_session_id)
            
            # Get current teacher
            teacher = Teacher.objects.get(user=request.user)
            
            # Step 1: Set Q (Qualified) - Teachers qualified for this subject
            qualified_teachers = Teacher.objects.filter(
                qualified_subjects__subject=class_session.subject
            ).distinct()
            
            # Exclude the requester
            qualified_teachers = qualified_teachers.exclude(id=teacher.id)
            
            # Ensure teachers are from same department (pilot phase constraint)
            qualified_teachers = qualified_teachers.filter(
                department=teacher.department
            )
            
            # Step 2: Set B (Busy) - Teachers busy at this time slot
            busy_teachers = Teacher.objects.filter(
                assigned_sessions__day_of_week=class_session.day_of_week,
                assigned_sessions__start_time__lt=class_session.end_time,
                assigned_sessions__end_time__gt=class_session.start_time,
                assigned_sessions__semester=class_session.semester,
                assigned_sessions__section=class_session.section
            ).distinct()
            
            # Step 3: Set L (On Leave) - Teachers on leave on this date
            on_leave_teachers = Teacher.objects.filter(
                leave_requests__date_of_leave=date_of_leave,
                leave_requests__status__in=[
                    LeaveRequest.Status.PENDING_HOD,
                    LeaveRequest.Status.APPROVED_OPEN,
                    LeaveRequest.Status.FILLED
                ]
            ).distinct()
            
            # Step 4: Result = Q - (B + L)
            available_teachers = qualified_teachers.exclude(
                id__in=busy_teachers.values_list('id', flat=True)
            ).exclude(
                id__in=on_leave_teachers.values_list('id', flat=True)
            )
            
            # Step 5: Sort by weekly workload (ascending)
            # Calculate workload for each teacher
            recommendations = []
            for teacher_obj in available_teachers:
                # Count weekly class sessions for this teacher
                weekly_workload = ClassSession.objects.filter(
                    assigned_teacher=teacher_obj
                ).count()
                
                # Calculate recommendation score
                # Lower workload = higher score
                score = 100 / (weekly_workload + 1)  # +1 to avoid division by zero
                
                recommendations.append({
                    'teacher': teacher_obj,
                    'weekly_workload': weekly_workload,
                    'is_available': True,
                    'is_qualified': True,
                    'is_on_leave': False,
                    'recommendation_score': round(score, 2)
                })
            
            # Sort by recommendation score (descending)
            recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
            
            # Serialize and return
            serializer = SubstituteRecommendationSerializer(recommendations, many=True)
            return Response(serializer.data)
            
        except ClassSession.DoesNotExist:
            return Response(
                {'error': 'Class session not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Teacher.DoesNotExist:
            return Response(
                {'error': 'Teacher profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class CreateLeaveRequestView(APIView):
    """
    API endpoint to create a leave request with selected teachers.
    POST /api/requests/create/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Create a leave request and substitution proposals.
        """
        serializer = CreateLeaveRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract validated data
        class_session = serializer.validated_data['class_session_id']
        date_of_leave = serializer.validated_data['date']
        reason = serializer.validated_data['reason']
        selected_teachers = serializer.validated_data['validated_teachers']
        message = serializer.validated_data.get('message', '')
        requester = serializer.validated_data['requester']
        
        # Use atomic transaction
        with transaction.atomic():
            # Step 1: Create LeaveRequest
            leave_request = LeaveRequest.objects.create(
                requester=requester,
                class_session=class_session,
                date_of_leave=date_of_leave,
                reason=reason,
                status=LeaveRequest.Status.PENDING_HOD
            )
            
            # Step 2: Create SubstitutionProposal for each selected teacher
            proposals = []
            for teacher in selected_teachers:
                proposal = SubstitutionProposal.objects.create(
                    request=leave_request,
                    proposed_teacher=teacher,
                    status=SubstitutionProposal.Status.QUEUED,
                    message_from_requester=message
                )
                proposals.append(proposal)
            
            # Step 3: Send notification to HOD (stub)
            # Find HOD of the department
            hod_users = User.objects.filter(
                is_hod=True,
                teacher_profile__department=requester.department
            )
            
            for hod_user in hod_users:
                try:
                    hod_teacher = Teacher.objects.get(user=hod_user)
                    self._send_fcm_notification(
                        hod_teacher.fcm_token,
                        title='New Leave Request',
                        body=f'{requester.full_name} has submitted a leave request for {date_of_leave}'
                    )
                except Teacher.DoesNotExist:
                    continue
            
            # Return created leave request with proposals
            leave_request_serializer = LeaveRequestSerializer(leave_request)
            
            return Response({
                'leave_request': leave_request_serializer.data,
                'proposals_created': len(proposals),
                'message': 'Leave request created successfully and sent to HOD for approval.'
            }, status=status.HTTP_201_CREATED)
    
    def _send_fcm_notification(self, token, title, body):
        """Stub for FCM notification sending."""
        print(f"[FCM Notification] To: {token}, Title: {title}, Body: {body}")