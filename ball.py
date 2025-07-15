import pygame
import time
from constants import BALL_RADIUS

class Ball:
    def __init__(self, x, y, width, height):
        self.width = width
        self.height = height
        self.rect = pygame.Rect(0, 0, BALL_RADIUS*2, BALL_RADIUS*2)
        self.rect.center = (x, y)
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        
        # Ball-Animation
        self.animation_timer = 0
        self.animation_interval = 0.2  # 0.2 Sekunden
        self.show_direction = False
        
        # Lade Ball-Bilder
        try:
            self.ball_normal = pygame.image.load("assets/ball.png")
            self.ball_left = pygame.image.load("assets/ball_left.png")
            self.ball_right = pygame.image.load("assets/ball_right.png")
            self.ball_up = pygame.image.load("assets/ball_up.png")
            self.ball_down = pygame.image.load("assets/ball_down.png")
            self.use_images = True
        except:
            # Fallback auf gezeichneten Ball
            self.use_images = False
            
    def update(self):
        self.pos += self.vel
        
        # Dynamische Animation basierend auf Geschwindigkeit
        current_time = time.time()
        # Basis-Intervall: 0.2 Sekunden, wird bei höherer Geschwindigkeit kürzer
        speed_factor = min(1.0, self.vel.length() / 5.0)  # Normalisierung auf max 5.0
        dynamic_interval = max(0.05, 0.2 - (speed_factor * 0.15))  # Min 0.05s, Max 0.2s
        
        if current_time - self.animation_timer > dynamic_interval:
            self.show_direction = not self.show_direction
            self.animation_timer = current_time
        
        if self.rect.left + self.vel.x < 0 or self.rect.right + self.vel.x > self.width:
            self.vel.x *= -0.8
        if self.rect.top + self.vel.y < 0 or self.rect.bottom + self.vel.y > self.height:
            self.vel.y *= -0.8
        self.pos.x = max(self.rect.width//2, min(self.width - self.rect.width//2, self.pos.x))
        self.pos.y = max(self.rect.height//2, min(self.height - self.rect.height//2, self.pos.y))
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.vel *= 0.98
        
    def reset(self, x, y):
        self.pos.update(x, y)
        self.vel.update(0, 0)
        self.rect.center = (int(x), int(y))
        
    def get_direction_image(self):
        """Bestimme das passende Ball-Bild basierend auf der Geschwindigkeit"""
        if not self.use_images or self.vel.length() < 0.5:
            return None
            
        # Bestimme Hauptrichtung
        if abs(self.vel.x) > abs(self.vel.y):
            # Horizontale Bewegung
            if self.vel.x > 0:
                return self.ball_right if self.show_direction else self.ball_normal
            else:
                return self.ball_left if self.show_direction else self.ball_normal
        else:
            # Vertikale Bewegung
            if self.vel.y > 0:
                return self.ball_down if self.show_direction else self.ball_normal
            else:
                return self.ball_up if self.show_direction else self.ball_normal
                
    def draw(self, surface):
        if self.use_images:
            ball_image = self.get_direction_image()
            if ball_image:
                # Skaliere Bild auf Ball-Größe
                scaled_image = pygame.transform.scale(ball_image, (BALL_RADIUS*2, BALL_RADIUS*2))
                image_rect = scaled_image.get_rect(center=self.rect.center)
                surface.blit(scaled_image, image_rect)
            else:
                # Fallback auf ball.png statt schwarzer Kreis
                scaled_image = pygame.transform.scale(self.ball_normal, (BALL_RADIUS*2, BALL_RADIUS*2))
                image_rect = scaled_image.get_rect(center=self.rect.center)
                surface.blit(scaled_image, image_rect)
        else:
            # Fallback auf ball.png statt schwarzer Kreis
            try:
                ball_normal = pygame.image.load("assets/ball.png")
                scaled_image = pygame.transform.scale(ball_normal, (BALL_RADIUS*2, BALL_RADIUS*2))
                image_rect = scaled_image.get_rect(center=self.rect.center)
                surface.blit(scaled_image, image_rect)
            except:
                # Nur als letzter Fallback schwarzer Kreis
                pygame.draw.circle(surface, (0,0,0), self.rect.center, BALL_RADIUS) 