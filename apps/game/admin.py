from django.contrib import admin

from .models import Answer, Guess, Player, Question, Room, Round, SyncResult

admin.site.register(Room)
admin.site.register(Player)
admin.site.register(Question)
admin.site.register(Round)
admin.site.register(Answer)
admin.site.register(Guess)
admin.site.register(SyncResult)
