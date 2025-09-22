from rest_framework import serializers

class GitlabTokenSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, write_only=True)

class GitlabProjectSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    name_with_namespace = serializers.CharField()
    description = serializers.CharField(allow_null=True, allow_blank=True)
    web_url = serializers.URLField()
    last_activity_at = serializers.DateTimeField(allow_null=True)

class GitlabCommitSerializer(serializers.Serializer):
    id = serializers.CharField()
    short_id = serializers.CharField()
    title = serializers.CharField()
    author_name = serializers.CharField()
    author_email = serializers.CharField()
    authored_date = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    message = serializers.CharField()
    ref_name = serializers.CharField(required=False, allow_null=True)
    branch_name = serializers.CharField(required=False, allow_null=True)

class DeveloperStatSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.CharField()
    additions = serializers.IntegerField()
    deletions = serializers.IntegerField()
    commits = serializers.IntegerField()
    branches = serializers.DictField(required=False, allow_null=True)

class DateRangeSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
