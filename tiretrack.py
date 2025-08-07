import pygame
import time
from constants import TRACK_LIFETIME

class TireTrack:
    def __init__(self, pos, angle, size, timestamp, track_type="gas"):
        self.pos = pygame.Vector2(pos)
        self.angle = angle
        self.size = size
        self.timestamp = timestamp
        self.alpha = 255
        self.track_type = track_type  # "gas", "brake", "accel"

class TireTrackManager:
    def __init__(self):
        self.tracks = []
        self.max_tracks = 500  # Reduced for better performance
        self.last_cleanup = 0  # For performance optimization
        
    def add(self, pos, angle, size, track_type="gas"):
        now = time.time()
        # Begrenze Anzahl von Spuren
        if len(self.tracks) >= self.max_tracks:
            self.tracks.pop(0)  # Entferne älteste Spur
        
        # Passe Größe basierend auf Spur-Typ an
        if track_type == "brake":
            size = (size[0] * 1.5, size[1] * 1.2)  # Brems-Spuren sind größer
        elif track_type == "accel":
            size = (size[0] * 0.8, size[1] * 1.1)  # Beschleunigungs-Spuren sind schmaler
        
        self.tracks.append(TireTrack(pos, angle, size, now, track_type))
        
    def draw(self, surface):
        now = time.time()
        
        # Only cleanup old tracks every 0.5 seconds for performance
        if now - self.last_cleanup > 0.5:
            self.tracks = [track for track in self.tracks if now - track.timestamp <= TRACK_LIFETIME]
            self.last_cleanup = now
        
        # Zeichne alle Spuren mit unterschiedlichen Eigenschaften
        for track in self.tracks:
            age = now - track.timestamp
            
            # Skip tracks that are too old (additional check for performance)
            if age > TRACK_LIFETIME:
                continue
            
            # Verschiedene Transparenzen basierend auf Spur-Typ
            if track.track_type == "brake":
                alpha = int(200 * max(0, 1 - age/TRACK_LIFETIME))  # Brems-Spuren sind dunkler
                base_color = (30, 30, 30)
            elif track.track_type == "accel":
                alpha = int(180 * max(0, 1 - age/TRACK_LIFETIME))  # Beschleunigungs-Spuren sind heller
                base_color = (50, 50, 50)
            else:  # gas
                alpha = int(255 * max(0, 1 - age/TRACK_LIFETIME))
                base_color = (40, 40, 40)
            
            # Skip nearly invisible tracks
            if alpha < 10:
                continue
            
            surf = pygame.Surface(track.size, pygame.SRCALPHA)
            surf.fill((*base_color, alpha))
            rotated = pygame.transform.rotate(surf, -track.angle)
            rect = rotated.get_rect(center=(int(track.pos.x), int(track.pos.y)))
            surface.blit(rotated, rect) 