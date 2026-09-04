import re
from django.db import models


# ==========================================================
# BOARD TYPE HIERARCHY
# ==========================================================

class BoardClass(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Board Classes"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BoardSubject(models.Model):
    board_class = models.ForeignKey(
        BoardClass,
        on_delete=models.CASCADE,
        related_name="subjects"
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["board_class", "name"]

    def __str__(self):
        return f"{self.board_class.name} - {self.name}"


class BoardChapter(models.Model):
    subject = models.ForeignKey(
        BoardSubject,
        on_delete=models.CASCADE,
        related_name="chapters"
    )
    title = models.CharField(max_length=200)
    chapter_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["subject", "chapter_number", "title"]

    def __str__(self):
        return f"{self.subject} | Ch {self.chapter_number}: {self.title}"


class BoardTopic(models.Model):
    chapter = models.ForeignKey(
        BoardChapter,
        on_delete=models.CASCADE,
        related_name="topics"
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["chapter", "order", "title"]

    def __str__(self):
        return f"{self.chapter.title} -> {self.title}"


class BoardSubTopic(models.Model):
    topic = models.ForeignKey(
        BoardTopic,
        on_delete=models.CASCADE,
        related_name="subtopics"
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["topic", "order", "title"]

    def __str__(self):
        return f"{self.topic.title} -> {self.title}"


# ==========================================================
# COMPETITIVE TYPE HIERARCHY
# ==========================================================

class CompetitiveExam(models.Model):
    title = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class CompetitiveModule(models.Model):
    exam = models.ForeignKey(
        CompetitiveExam,
        on_delete=models.CASCADE,
        related_name="modules"
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["exam", "order"]

    def __str__(self):
        return f"{self.exam.title} - {self.title}"


class CompetitiveSubModule(models.Model):
    module = models.ForeignKey(
        CompetitiveModule,
        on_delete=models.CASCADE,
        related_name="submodules"
    )
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["module", "order"]

    def __str__(self):
        return f"{self.module.title} -> {self.title}"


# ==========================================================
# QUESTION BANK
# ==========================================================

class Question(models.Model):

    FLOW_CHOICES = (
        ("board", "Board Type"),
        ("competitive", "Competitive Type"),
    )

    OPTION_CHOICES = (
        ("A", "Option A"),
        ("B", "Option B"),
        ("C", "Option C"),
        ("D", "Option D"),
    )

    assessment_flow = models.CharField(
        max_length=20,
        choices=FLOW_CHOICES,
        default="board"
    )

    # Scoping Links
    board_subtopic = models.ForeignKey(
        BoardSubTopic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions"
    )
    competitive_submodule = models.ForeignKey(
        CompetitiveSubModule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions"
    )

    # Text Content
    question_text = models.TextField(blank=True)
    question_image = models.ImageField(upload_to="questions/", blank=True, null=True)

    # Options (Text + Images)
    option_a = models.CharField(max_length=255, blank=True)
    option_a_image = models.ImageField(upload_to="options/", blank=True, null=True)

    option_b = models.CharField(max_length=255, blank=True)
    option_b_image = models.ImageField(upload_to="options/", blank=True, null=True)

    option_c = models.CharField(max_length=255, blank=True)
    option_c_image = models.ImageField(upload_to="options/", blank=True, null=True)

    option_d = models.CharField(max_length=255, blank=True)
    option_d_image = models.ImageField(upload_to="options/", blank=True, null=True)

    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES)

    # Video Resources
    explanation = models.TextField(blank=True)
    youtube_url = models.URLField(blank=True, null=True)
    youtube_thumbnail_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.youtube_url:
            video_id = self.extract_youtube_id(self.youtube_url)
            if video_id:
                self.youtube_thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            else:
                self.youtube_thumbnail_url = ""
        else:
            self.youtube_thumbnail_url = ""
        super().save(*args, **kwargs)


    @staticmethod
    def extract_youtube_id(url):
        if not url:
            return None
        regex = r"(?:v=|\/)([0-9A-Za-z_-]{11})"
        match = re.search(regex, url)
        if match:
            return match.group(1)
        return None

    @property
    def youtube_embed_url(self):
        if self.youtube_url:
            video_id = self.extract_youtube_id(self.youtube_url)
            if video_id:
                return f"https://www.youtube-nocookie.com/embed/{video_id}"
        return None

    @property
    def get_options(self):
        options = {}
        if self.option_a:
            options['A'] = self.option_a
        if self.option_b:
            options['B'] = self.option_b
        if self.option_c:
            options['C'] = self.option_c
        if self.option_d:
            options['D'] = self.option_d
        return options

    def __str__(self):
        text = self.question_text[:50] if self.question_text else "[Image Question]"
        return f"[{self.get_assessment_flow_display()}] {text}"