import pygame
import math

class Auto:
    def __init__(self, image, x, y, scale_factor, bounds):
        self.original_image = image
        self.image = image
        self.rect = self.image.get_rect(center=(x, y))
        self.position = pygame.Vector2(x, y)
        self.velocity = 0.0  # Skalar
        self.angle = 0.0  # Grad
        self.scale_factor = scale_factor
        self.bounds = bounds
        # Arcade-Parameter
        self.acceleration = 0.5
        self.max_speed = 5.0
        self.turn_speed = 3.0
        self.friction = 0.98
        # Drift
        self.drifting = False
        self.drift_turn_speed = self.turn_speed * 2.0
        self.drift_friction = 0.995
        self.drift_vector = pygame.Vector2(math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle)))
        self.drift_lerp = 0.15  # Wie schnell drift_vector Richtung angle annimmt

    def update(self):
        # Drift-Logik
        if self.drifting:
            turn_speed = self.drift_turn_speed
            friction = self.drift_friction
            # Drift-Vektor langsam an neue Richtung anpassen
            direction = pygame.Vector2(math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle)))
            self.drift_vector = self.drift_vector.lerp(direction, self.drift_lerp)
            move_vec = self.drift_vector * self.velocity
        else:
            turn_speed = self.turn_speed
            friction = self.friction
            direction = pygame.Vector2(math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle)))
            self.drift_vector = direction
            move_vec = direction * self.velocity
        # Position updaten
        self.position += move_vec
        # Spielfeldbegrenzung
        w, h = self.bounds
        self.position.x = max(self.rect.width//2, min(w - self.rect.width//2, self.position.x))
        self.position.y = max(self.rect.height//2, min(h - self.rect.height//2, self.position.y))
        self.rect.center = (int(self.position.x), int(self.position.y))
        # Geschwindigkeit/Reibung
        self.velocity *= friction
        # Bildwinkel
        self.image = pygame.transform.rotate(self.original_image, -self.angle)
        # Drift-Reset
        self.drifting = False

    def accelerate(self):
        self.velocity += self.acceleration
        if self.velocity > self.max_speed:
            self.velocity = self.max_speed

    def reverse(self):
        self.velocity -= self.acceleration
        if self.velocity < -self.max_speed/2:
            self.velocity = -self.max_speed/2

    def brake(self):
        self.velocity *= 0.9

    def steer_left(self):
        if abs(self.velocity) > 0.1:
            if self.drifting:
                self.angle -= self.drift_turn_speed
            else:
                self.angle -= self.turn_speed
            self.angle %= 360

    def steer_right(self):
        if abs(self.velocity) > 0.1:
            if self.drifting:
                self.angle += self.drift_turn_speed
            else:
                self.angle += self.turn_speed
            self.angle %= 360

    def drift(self):
        self.drifting = True

    def draw(self, surface):
        rotated_rect = self.image.get_rect(center=self.rect.center)
        surface.blit(self.image, rotated_rect) 