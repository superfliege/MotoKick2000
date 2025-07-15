import pygame

class GoalPosts:
    def __init__(self, width, height, post_radius, gap):
        self.post_radius = post_radius
        self.gap = gap
        self.center = height // 2
        self.y1 = self.center - gap // 2
        self.y2 = self.center + gap // 2
        self.left1 = (0, self.y1)
        self.left2 = (0, self.y2)
        self.right1 = (width, self.y1)
        self.right2 = (width, self.y2)
        self.posts = [self.left1, self.left2, self.right1, self.right2]
    def draw(self, surface):
        for post in self.posts:
            pygame.draw.circle(surface, (0,0,0), post, self.post_radius) 