import pygame

class Banden:
    def __init__(self, width, height, banden_breite):
        self.width = width
        self.height = height
        self.banden_breite = banden_breite

    def draw(self, surface):
        # Schwarzer Rand
        pygame.draw.rect(surface, (0,0,0), (0, 0, self.width, self.height), self.banden_breite)

    def draw_field(self, surface, goals):
        # Weiße Linien: Außenlinien
        line_width = 6
        field_rect = pygame.Rect(self.banden_breite//2, self.banden_breite//2, self.width-self.banden_breite, self.height-self.banden_breite)
        pygame.draw.rect(surface, (255,255,255), field_rect, line_width)
        # Mittellinie
        pygame.draw.line(surface, (255,255,255), (self.width//2, self.banden_breite), (self.width//2, self.height-self.banden_breite), line_width)
        # Mittelkreis
        center = (self.width//2, self.height//2)
        pygame.draw.circle(surface, (255,255,255), center, 120, line_width)
        # Torraum links
        torraum_breite = 120
        torraum_tiefe = 220
        pygame.draw.rect(surface, (255,255,255), (self.banden_breite, self.height//2-torraum_tiefe//2, torraum_breite, torraum_tiefe), line_width)
        # Torraum rechts
        pygame.draw.rect(surface, (255,255,255), (self.width-torraum_breite-self.banden_breite, self.height//2-torraum_tiefe//2, torraum_breite, torraum_tiefe), line_width)
        # Tore (optional, als Linie)
        pygame.draw.line(surface, (255,255,255), (self.banden_breite, goals.y1), (self.banden_breite, goals.y2), line_width)
        pygame.draw.line(surface, (255,255,255), (self.width-self.banden_breite, goals.y1), (self.width-self.banden_breite, goals.y2), line_width) 