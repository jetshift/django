from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class ChartsDatabasesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from app.models import JSDatabase
        from django.db.models import Count

        try:
            raw_counts = (
                JSDatabase.objects
            ).values('type').annotate(count=Count('type')).order_by('-count')

            # Capitalize the first letter of each status
            status_counts = [
                {'type': item['type'].capitalize(), 'count': item['count']}
                for item in raw_counts
            ]

            return Response({
                "success": True,
                "message": "Successfully fetched database chart data",
                "types": status_counts
            })
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Failed to fetch chart data: {str(e)}",
                "types": []
            })


class ChartsETLTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from app.models import JSSubTask
        from django.db.models import Count

        try:
            type_param = self.request.query_params.get('type')

            raw_counts = (
                JSSubTask.objects
                .filter(task__type=type_param) if type_param else JSSubTask.objects
            ).values('status').annotate(count=Count('status')).order_by('-count')

            # Capitalize the first letter of each status
            status_counts = [
                {'status': item['status'].capitalize(), 'count': item['count']}
                for item in raw_counts
            ]

            return Response({
                "success": True,
                "message": "Successfully fetched task chart data",
                "statuses": status_counts
            })
        except Exception as e:
            return Response({
                "success": False,
                "message": f"Failed to fetch chart data: {str(e)}",
                "statuses": []
            })
