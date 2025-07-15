import pygame
from constants import BALL_RADIUS

class Ball:
    def __init__(self, x, y, width, height):
        self.width = width
        self.height = height
        self.rect = pygame.Rect(0, 0, BALL_RADIUS*2, BALL_RADIUS*2)
        self.rect.center = (x, y)
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
    def update(self):
        self.pos += self.vel
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
    def draw(self, surface):
        pygame.draw.circle(surface, (0,0,0), self.rect.center, BALL_RADIUS) 