from datetime import datetime, timedelta

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

class MockRevisionsView(APIView):
    permission_classes = [AllowAny]  # Allow unauthenticated access for testing

    Temporary mock endpoint for page revisions while database issues are resolved.
    This provides the same revision data that was implemented in the serializer.

    def get(self, request, page_id):
        """Return mock revision data for a specific page."""
        now = datetime.now()

        mock_revisions = [
            {
                "id": f"rev-{page_id}-1",
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "created_by_email": "john.doe@example.com",
                "created_by_name": "John Doe",
                "is_published_snapshot": True,
                "is_autosave": False,
                "comment": "Published latest changes",
                "block_count": 5,
                "revision_type": "published",
            },
            {
                "id": f"rev-{page_id}-2",
                "created_at": (now - timedelta(days=1)).isoformat(),
                "created_by_email": "jane.smith@example.com",
                "created_by_name": "Jane Smith",
                "is_published_snapshot": False,
                "is_autosave": True,
                "comment": "",
                "block_count": 5,
                "revision_type": "autosave",
            },
            {
                "id": f"rev-{page_id}-3",
                "created_at": (now - timedelta(days=3)).isoformat(),
                "created_by_email": "admin@example.com",
                "created_by_name": "Admin",
                "is_published_snapshot": False,
                "is_autosave": False,
                "comment": "Initial version",
                "block_count": 3,
                "revision_type": "manual",
            },
        ]

        return Response({"page_id": page_id, "revisions": mock_revisions})
