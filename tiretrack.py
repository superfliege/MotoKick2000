import pygame
import time
from constants import TRACK_LIFETIME

class TireTrack:
    def __init__(self, pos, angle, size, timestamp):
        self.pos = pygame.Vector2(pos)
        self.angle = angle
        self.size = size
        self.timestamp = timestamp
        self.alpha = 255

class TireTrackManager:
    def __init__(self):
        self.tracks = []
        self.max_tracks = 80  # Etwas mehr Spuren erlauben
        
    def add(self, pos, angle, size):
        now = time.time()
        # Begrenze Anzahl von Spuren
        if len(self.tracks) >= self.max_tracks:
            self.tracks.pop(0)  # Entferne älteste Spur
        self.tracks.append(TireTrack(pos, angle, size, now))
        
    def draw(self, surface):
        now = time.time()
        # Entferne alte Spuren
        self.tracks = [track for track in self.tracks if now - track.timestamp <= TRACK_LIFETIME]
        
        # Zeichne alle Spuren (aber mit Begrenzung)
        for track in self.tracks:
            age = now - track.timestamp
            alpha = int(255 * max(0, 1 - age/TRACK_LIFETIME))
            surf = pygame.Surface(track.size, pygame.SRCALPHA)
            surf.fill((40, 40, 40, alpha))
            rotated = pygame.transform.rotate(surf, -track.angle)
            rect = rotated.get_rect(center=(int(track.pos.x), int(track.pos.y)))
            surface.blit(rotated, rect) 