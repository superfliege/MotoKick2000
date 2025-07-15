import pygame
import sys
import time
import math
from auto import Auto
from ball import Ball
from tiretrack import TireTrackManager
from goalposts import GoalPosts
from banden import Banden
from constants import BALL_RADIUS, BANDEN_BREITE, TRACK_LIFETIME, TRACK_MARK_TIME
from car_ai import CarAI

class Game:
    WIDTH = 1740
    HEIGHT = 980
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("MotoKick2000")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 48)
        # Versuche Retro-Font, fallback auf Courier New
        try:
            self.menu_font = pygame.font.Font("assets/PressStart2P.ttf", 48)
        except:
            self.menu_font = pygame.font.SysFont("Courier New", 48, bold=True)
        self.field = self.load_field()
        self.tiretracks = TireTrackManager()
        self.banden = Banden(self.WIDTH, self.HEIGHT, BANDEN_BREITE)
        self.goals = GoalPosts(self.WIDTH, self.HEIGHT, 20, 120)
        self.ball = Ball(self.WIDTH//2, self.HEIGHT//2, self.WIDTH, self.HEIGHT)
        car_blue_img = pygame.transform.scale(pygame.image.load("assets/car_blue.png"), (2*pygame.image.load("assets/car_blue.png").get_width(), 2*pygame.image.load("assets/car_blue.png").get_height()))
        car_red_img = pygame.transform.scale(pygame.image.load("assets/car_red.png"), (2*pygame.image.load("assets/car_red.png").get_width(), 2*pygame.image.load("assets/car_red.png").get_height()))
        self.car_blue = Auto(car_blue_img, 80, self.HEIGHT//2, 2.0, (self.WIDTH, self.HEIGHT))
        self.car_red = Auto(car_red_img, self.WIDTH-80, self.HEIGHT//2, 2.0, (self.WIDTH, self.HEIGHT))
        self.car_red.angle = 180
        self.score_blue = 0
        self.score_red = 0
        self.car_blue_last_action = None
        self.car_red_last_action = None
        self.car_blue_track_timer = 0
        self.car_red_track_timer = 0
        self.menu_background = pygame.image.load("assets/menu_backround.png")
        self.menu_items = ["Spieler 1", "Spieler 2", "Spieler 3", "Spieler 4", "Beenden"]
        self.menu_selected = 0
        self.game_timer = 120  # 2 Minuten in Sekunden
        self.game_start_time = None
    def load_field(self):
        field = pygame.image.load("assets/field.png")
        return field
    def add_tire_tracks(self, car, action):
        car_length = car.rect.height // 2
        car_width = car.rect.width // 2
        angle_rad = math.radians(car.angle)
        offset_back = pygame.Vector2(-math.cos(angle_rad), -math.sin(angle_rad)) * (car_length * 0.7)
        offset_side = pygame.Vector2(-math.sin(angle_rad), math.cos(angle_rad)) * (car_width * 0.5)
        rear_left = car.position + offset_back + offset_side
        rear_right = car.position + offset_back - offset_side
        size = (max(4, car.rect.width//10), max(10, car.rect.height//6))
        self.tiretracks.add(rear_left, car.angle, size)
        self.tiretracks.add(rear_right, car.angle, size)
    def reset_ball(self):
        self.ball.reset(self.WIDTH//2, self.HEIGHT//2)
    def show_menu(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.menu_selected = (self.menu_selected - 1) % len(self.menu_items)
                    if event.key == pygame.K_RIGHT:
                        self.menu_selected = (self.menu_selected + 1) % len(self.menu_items)
                    if event.key == pygame.K_RETURN:
                        if self.menu_items[self.menu_selected] == "Beenden":
                            pygame.quit()
                            sys.exit()
                        else:
                            return self.menu_selected + 1
            # Schwarzer Hintergrund
            self.screen.fill((0, 0, 0))
            # Menübild darüber
            self.screen.blit(pygame.transform.scale(self.menu_background, (self.WIDTH, self.HEIGHT)), (0, 0))
            # Schwarzer Hintergrundbalken für Menü
            menu_bar_height = 90
            menu_bar_rect = pygame.Rect(0, self.HEIGHT - menu_bar_height, self.WIDTH, menu_bar_height)
            pygame.draw.rect(self.screen, (0, 0, 0), menu_bar_rect)
            # Menüeinträge horizontal am unteren Rand, zentriert
            menu_surfs = [self.menu_font.render(item, True, (0,255,0) if i==self.menu_selected else (255,255,255)) for i,item in enumerate(self.menu_items)]
            total_width = sum(surf.get_width() for surf in menu_surfs) + (len(menu_surfs)-1)*60
            start_x = (self.WIDTH - total_width)//2
            y = self.HEIGHT - 60
            x = start_x
            for surf in menu_surfs:
                rect = surf.get_rect(midbottom=(x + surf.get_width()//2, y))
                self.screen.blit(surf, rect)
                x += surf.get_width() + 60
            # "By Superfliege" unten rechts
            by_font = pygame.font.SysFont("Courier New", 22, bold=True)
            by_text = by_font.render("By Superfliege", True, (200, 200, 200))
            by_rect = by_text.get_rect(bottomright=(self.WIDTH-18, self.HEIGHT-10))
            self.screen.blit(by_text, by_rect)
            pygame.display.flip()
            self.clock.tick(60)
    def run(self):
        player_count = self.show_menu()
        # Timer starten
        self.game_start_time = time.time()
        self.game_timer = 120  # Reset timer
        car_imgs = [
            pygame.transform.scale(pygame.image.load("assets/car_red.png"), (2*pygame.image.load("assets/car_red.png").get_width(), 2*pygame.image.load("assets/car_red.png").get_height())),
            pygame.transform.scale(pygame.image.load("assets/car_blue.png"), (2*pygame.image.load("assets/car_blue.png").get_width(), 2*pygame.image.load("assets/car_blue.png").get_height())),
            pygame.transform.scale(pygame.image.load("assets/car_yellow.png"), (2*pygame.image.load("assets/car_yellow.png").get_width(), 2*pygame.image.load("assets/car_yellow.png").get_height())),
            pygame.transform.scale(pygame.image.load("assets/car_pink.png"), (2*pygame.image.load("assets/car_pink.png").get_width(), 2*pygame.image.load("assets/car_pink.png").get_height())),
        ]
        # Neue Startpositionen und Teams
        left_x = 120
        right_x = self.WIDTH-120
        center_y = self.HEIGHT//2
        top_y = 220
        bottom_y = self.HEIGHT-220
        self.cars = []
        if player_count == 1:
            # Nur rotes Auto (Spieler) links
            self.cars.append(Auto(car_imgs[0], left_x, center_y, 2.0, (self.WIDTH, self.HEIGHT)))
            self.cars[0].angle = 0
        elif player_count == 2:
            # Spieler: rot links, KI: blau rechts
            self.cars.append(Auto(car_imgs[0], left_x, center_y, 2.0, (self.WIDTH, self.HEIGHT)))
            self.cars[0].angle = 0
            self.cars.append(CarAI(car_imgs[1], right_x, center_y, 2.0, (self.WIDTH, self.HEIGHT), team='blue', side='right'))
            self.cars[1].angle = 180
        elif player_count == 3:
            # Spieler: rot links, KI: blau rechts, gelb rechts
            self.cars.append(Auto(car_imgs[0], left_x, center_y, 2.0, (self.WIDTH, self.HEIGHT)))
            self.cars[0].angle = 0
            self.cars.append(CarAI(car_imgs[1], right_x, top_y, 2.0, (self.WIDTH, self.HEIGHT), team='blue', side='right'))
            self.cars[1].angle = 180
            self.cars.append(CarAI(car_imgs[2], right_x, bottom_y, 2.0, (self.WIDTH, self.HEIGHT), team='yellow', side='right'))
            self.cars[2].angle = 180
        elif player_count == 4:
            # Team: rot+blau (links) vs. gelb+pink (rechts)
            self.cars.append(Auto(car_imgs[0], left_x, top_y, 2.0, (self.WIDTH, self.HEIGHT)))
            self.cars[0].angle = 0
            self.cars.append(CarAI(car_imgs[1], left_x, bottom_y, 2.0, (self.WIDTH, self.HEIGHT), team='blue', side='left'))
            self.cars[1].angle = 0
            self.cars.append(CarAI(car_imgs[2], right_x, top_y, 2.0, (self.WIDTH, self.HEIGHT), team='yellow', side='right'))
            self.cars[2].angle = 180
            self.cars.append(CarAI(car_imgs[3], right_x, bottom_y, 2.0, (self.WIDTH, self.HEIGHT), team='pink', side='right'))
            self.cars[3].angle = 180
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            keys = pygame.key.get_pressed()
            now = time.time()
            # Timer-Logik
            elapsed_time = now - self.game_start_time
            remaining_time = max(0, self.game_timer - elapsed_time)
            if remaining_time <= 0:
                # Spielende - zeige finalen Spielstand
                self.show_final_score()
                return  # Zurück zum Menü
            # Steuerung für Spieler (immer erstes Auto)
            player_car = self.cars[0]
            prev_vel = player_car.velocity
            action = None
            if keys[pygame.K_w]:
                player_car.accelerate()
                if prev_vel < 0.5 and player_car.velocity >= 0.5:
                    action = 'gas'
                    self.car_red_track_timer = now + TRACK_MARK_TIME
            if keys[pygame.K_s]:
                player_car.reverse()
                if prev_vel > -0.1 and player_car.velocity <= -0.1:
                    action = 'brake'
                    self.car_red_track_timer = now + TRACK_MARK_TIME
            if keys[pygame.K_a]:
                player_car.steer_left()
            if keys[pygame.K_d]:
                player_car.steer_right()
            if keys[pygame.K_KP0]:
                player_car.drift()
            if self.car_red_track_timer > now:
                if keys[pygame.K_w]:
                    self.add_tire_tracks(player_car, 'gas')
                if keys[pygame.K_s]:
                    self.add_tire_tracks(player_car, 'brake')
            # Spielerauto updaten (Bewegung)
            player_car.update()
            # KI-Logik für alle CarAI
            for i, car in enumerate(self.cars[1:], start=1):
                prev_vel_ai = car.velocity
                if isinstance(car, CarAI):
                    teammates = [c for c in self.cars if c is not car and getattr(c, 'team', None) == car.team]
                    opponents = [c for c in self.cars if c is not car and getattr(c, 'team', None) != car.team]
                    car.update_ai(self.ball, self.goals, teammates, opponents)
                else:
                    car.update()
                # Reifenspuren für KI/andere Autos bei Beschleunigung aus dem Stand
                if prev_vel_ai < 0.5 and car.velocity >= 0.5:
                    if not hasattr(self, 'car_track_timers'):
                        self.car_track_timers = {}
                    self.car_track_timers[i] = now + TRACK_MARK_TIME
                if hasattr(self, 'car_track_timers') and i in self.car_track_timers and self.car_track_timers[i] > now:
                    if car.velocity > 0:
                        self.add_tire_tracks(car, 'gas')
                    elif car.velocity < 0:
                        self.add_tire_tracks(car, 'brake')
            self.ball.update()
            # Kollisionen für alle Autos
            for i, car1 in enumerate(self.cars):
                car1_center = car1.rect.center
                car1_pos = car1.position
                car1_rect = car1.rect
                for j, car2 in enumerate(self.cars):
                    if i >= j:
                        continue
                    # Schneller Bounding-Box-Check
                    if not car1_rect.colliderect(car2.rect):
                        continue
                    car2_center = car2.rect.center
                    car2_pos = car2.position
                    car_dist = pygame.Vector2(car1_center).distance_to(car2_center)
                    min_dist = (car1_rect.width + car2.rect.width) // 2 * 0.7
                    if car_dist < min_dist:
                        direction = pygame.Vector2(car1_center) - pygame.Vector2(car2_center)
                        if direction.length() == 0:
                            direction = pygame.Vector2(1,0)
                        direction = direction.normalize()
                        overlap = min_dist - car_dist
                        # Bounce: Schiebe Autos auseinander
                        car1_pos += direction * (overlap/2)
                        car2_pos -= direction * (overlap/2)
                        car1_rect.center = (int(car1_pos.x), int(car1_pos.y))
                        car2.rect.center = (int(car2_pos.x), int(car2_pos.y))
                        # Richtungsabhängiger Velocity-Impuls (Vektor-Bounce)
                        bounce_strength = 0.4
                        min_bounce = 0.2
                        # Impuls für car1 (weg von car2)
                        car1_vec = pygame.Vector2(math.cos(math.radians(car1.angle)), math.sin(math.radians(car1.angle)))
                        car1_bounce = direction * max(abs(car1.velocity), min_bounce) * bounce_strength
                        car1_vec = car1_vec.lerp(car1_bounce.normalize(), 0.9)
                        car1.velocity = car1_vec.length()
                        # car1.angle bleibt unverändert
                        # Impuls für car2 (weg von car1)
                        car2_vec = pygame.Vector2(math.cos(math.radians(car2.angle)), math.sin(math.radians(car2.angle)))
                        car2_bounce = -direction * max(abs(car2.velocity), min_bounce) * bounce_strength
                        car2_vec = car2_vec.lerp(car2_bounce.normalize(), 0.9)
                        car2.velocity = car2_vec.length()
                        # car2.angle bleibt unverändert
            # Kollision Auto mit Pfosten
            for car in self.cars:
                for post in self.goals.posts:
                    car_center = pygame.Vector2(car.rect.center)
                    dist = car_center.distance_to(post)
                    min_dist = self.goals.post_radius + car.rect.width//2 * 0.7
                    if dist < min_dist:
                        direction = car_center - pygame.Vector2(post)
                        if direction.length() == 0:
                            direction = pygame.Vector2(1,0)
                        direction = direction.normalize()
                        overlap = min_dist - dist
                        car.position += direction * overlap
                        car.rect.center = (int(car.position.x), int(car.position.y))
                        car.velocity *= -0.5
            # Ball-Auto-Kollision
            for car in self.cars:
                ball_center = pygame.Vector2(self.ball.rect.center)
                closest = closest_point_on_rotated_rect(ball_center, car)
                dist = ball_center.distance_to(closest)
                if dist < BALL_RADIUS:
                    direction = (ball_center - closest)
                    if direction.length() == 0:
                        direction = pygame.Vector2(1,0)
                    direction = direction.normalize()
                    overlap = BALL_RADIUS - dist
                    self.ball.pos += direction * overlap
                    self.ball.rect.center = (int(self.ball.pos.x), int(self.ball.pos.y))
                    v_norm = self.ball.vel.dot(direction)
                    if v_norm < 0:
                        self.ball.vel = self.ball.vel - direction * v_norm * 2
                    if car.velocity > 0:
                        self.ball.vel += direction * abs(car.velocity) * 1.2
                    else:
                        self.ball.vel += direction * 3
                    car.velocity *= 0.7
                    max_ball_speed = 8 * (self.WIDTH / 256)
                    if self.ball.vel.length() > max_ball_speed:
                        self.ball.vel.scale_to_length(max_ball_speed)
            # Ball-Pfosten-Kollision
            for post in self.goals.posts:
                dist = pygame.Vector2(self.ball.rect.center).distance_to(post)
                if dist < self.goals.post_radius + BALL_RADIUS:
                    direction = pygame.Vector2(self.ball.rect.center) - pygame.Vector2(post)
                    if direction.length() == 0:
                        direction = pygame.Vector2(1,0)
                    direction = direction.normalize()
                    self.ball.vel = direction * self.ball.vel.length() * 0.8
                    overlap = self.goals.post_radius + BALL_RADIUS - dist
                    self.ball.pos += direction * overlap
                    self.ball.rect.center = (int(self.ball.pos.x), int(self.ball.pos.y))
            # Tore prüfen
            y1 = self.goals.y1
            y2 = self.goals.y2
            if (self.ball.rect.left <= 0 and y1 < self.ball.rect.centery < y2):
                self.score_red += 1
                self.reset_ball()
            if (self.ball.rect.right >= self.WIDTH and y1 < self.ball.rect.centery < y2):
                self.score_blue += 1
                self.reset_ball()
            self.draw(remaining_time)
            self.clock.tick(60)
    def draw(self, remaining_time):
        self.screen.fill((0,0,0))
        self.screen.blit(self.field, (0, 0))
        self.banden.draw_field(self.screen, self.goals)
        self.banden.draw(self.screen)
        self.goals.draw(self.screen)
        self.tiretracks.draw(self.screen)
        self.ball.draw(self.screen)
        for car in self.cars:
            car.draw(self.screen)
        score_text = self.font.render(f"{self.score_blue} : {self.score_red}", True, (255,255,255))
        self.screen.blit(score_text, (self.WIDTH//2-score_text.get_width()//2, int(20)))
        # Countdown oben rechts
        minutes = int(remaining_time) // 60
        seconds = int(remaining_time) % 60
        countdown_text = self.font.render(f"{minutes:02d}:{seconds:02d}", True, (255, 255, 255))
        countdown_rect = countdown_text.get_rect(topright=(self.WIDTH - 20, 20))
        self.screen.blit(countdown_text, countdown_rect)
        pygame.display.flip()

    def show_final_score(self):
        """Zeige finalen Spielstand an und warte auf Tastendruck"""
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    return  # Zurück zum Menü
            
            # Hintergrund zeichnen
            self.screen.blit(pygame.transform.scale(self.menu_background, (self.WIDTH, self.HEIGHT)), (0, 0))
            
            # Schwarzer Hintergrundbalken
            menu_bar_height = 120
            menu_bar_rect = pygame.Rect(0, self.HEIGHT//2 - menu_bar_height//2, self.WIDTH, menu_bar_height)
            pygame.draw.rect(self.screen, (0, 0, 0), menu_bar_rect)
            
            # Finaler Spielstand
            final_text = self.menu_font.render("SPIELENDE!", True, (255, 255, 0))
            score_text = self.menu_font.render(f"Finaler Spielstand: {self.score_blue} : {self.score_red}", True, (255, 255, 255))
            press_text = self.menu_font.render("Drücke eine Taste", True, (200, 200, 200))
            
            # Texte zentrieren
            final_rect = final_text.get_rect(center=(self.WIDTH//2, self.HEIGHT//2 - 40))
            score_rect = score_text.get_rect(center=(self.WIDTH//2, self.HEIGHT//2))
            press_rect = press_text.get_rect(center=(self.WIDTH//2, self.HEIGHT//2 + 40))
            
            self.screen.blit(final_text, final_rect)
            self.screen.blit(score_text, score_rect)
            self.screen.blit(press_text, press_rect)
            
            pygame.display.flip()
            self.clock.tick(60)

def closest_point_on_rotated_rect(ball_center, car):
    # Transformiere Ball in lokale Koordinaten des Autos
    angle_rad = math.radians(car.angle)
    cos_a = math.cos(-angle_rad)
    sin_a = math.sin(-angle_rad)
    rel = pygame.Vector2(ball_center) - car.position
    local_x = rel.x * cos_a - rel.y * sin_a
    local_y = rel.x * sin_a + rel.y * cos_a
    # Clampe auf Rechteck
    half_w = car.rect.width / 2
    half_h = car.rect.height / 2
    clamped_x = max(-half_w, min(half_w, local_x))
    clamped_y = max(-half_h, min(half_h, local_y))
    # Transformiere zurück in Weltkoordinaten
    world_x = clamped_x * cos_a + clamped_y * sin_a + car.position.x
    world_y = -clamped_x * sin_a + clamped_y * cos_a + car.position.y
    return pygame.Vector2(world_x, world_y)

if __name__ == "__main__":
    Game().run() 
if __name__ == "__main__":
    Game().run() 