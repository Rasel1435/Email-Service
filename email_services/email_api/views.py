from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .utils import fetch_email_threads, send_email, fetch_all_inbox_emails


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user        
        return Response({
            "message": f"Welcome {user.username} to the Email Service API!",
            "user": {
                "username": user.username,
                "email": user.email
            },
            "endpoints": {
                "fetch_threads": "/api/threads/",
                "send_email": "/api/send/",
                "inbox": "/api/inbox/"
            }
        })


class EmailThreadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sender = request.data.get('email')
        if not sender:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        threads = fetch_email_threads(request.user, sender)
        if 'error' in threads:
            return Response(threads, status=status.HTTP_400_BAD_REQUEST)

        return Response(threads)


class SendEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        to = request.data.get('to')
        subject = request.data.get('subject')
        body = request.data.get('body')
        thread_id = request.data.get('thread_id')

        if not to or not body:
            return Response({'error': 'Both "to" and "body" are required'}, status=status.HTTP_400_BAD_REQUEST)

        if not subject and not thread_id:
            return Response({'error': 'Either "subject" or "thread_id" is required'}, status=status.HTTP_400_BAD_REQUEST)

        result = send_email(
            user=request.user,
            to=to,
            subject=subject,
            body=body,
            thread_id=thread_id
        )

        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)


class InboxView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        inbox_threads = fetch_all_inbox_emails(user)
        if 'error' in inbox_threads:
            return Response(inbox_threads, status=status.HTTP_400_BAD_REQUEST)
        return Response(inbox_threads)
