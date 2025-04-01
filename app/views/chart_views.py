from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class ChartsETLTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from app.models import MigrationTask
        from django.db.models import Count

        try:
            type_param = self.request.query_params.get('type')

            raw_counts = (
                MigrationTask.objects
                .filter(migrate_table__type=type_param) if type_param else MigrationTask.objects
            ).values('status').annotate(count=Count('status')).order_by('-count')

            # Capitalize the first letter of each status
            status_counts = [
                {'status': item['status'].capitalize(), 'count': item['count']}
                for item in raw_counts
            ]

            return Response({
                "success": True,
                "message": "Successfully fetched chart data",
                "statuses": status_counts
            })
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Failed to fetch chart data: {str(e)}",
                "statuses": []
            })


class ChartsDatabasesView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "Databases chart data"})
