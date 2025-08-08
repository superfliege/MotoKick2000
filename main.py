import pygame
import sys
import time
import math
import threading
import queue
from auto import Auto
from ball import Ball
from tiretrack import TireTrackManager
from goalposts import GoalPosts
from banden import Banden
from constants import BALL_RADIUS, BANDEN_BREITE, TRACK_LIFETIME, TRACK_MARK_TIME
from car_ai import CarAI
import os
import socket
import threading
import random



class Game:
    WIDTH = 1740
    HEIGHT = 980
    def __init__(self):
        pygame.init()
        flags = pygame.HWSURFACE | pygame.DOUBLEBUF
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT), flags)
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
        self.goals = GoalPosts(self.WIDTH, self.HEIGHT, 10, 130)
        self.ball = Ball(self.WIDTH//2, self.HEIGHT//2, self.WIDTH, self.HEIGHT)
        # Assets vorladen (konvertiert) und 4x skalieren (Autos doppelt so groß wie bisher 2x)
        self.CAR_SCALE_MULT = 4.0
        self.img_red = self._load_and_scale("assets/car_red.png", self.CAR_SCALE_MULT)
        self.img_blue = self._load_and_scale("assets/car_blue.png", self.CAR_SCALE_MULT)
        self.img_yellow = self._load_and_scale("assets/car_yellow.png", self.CAR_SCALE_MULT)
        self.img_pink = self._load_and_scale("assets/car_pink.png", self.CAR_SCALE_MULT)
        self.score_blue = 0
        self.score_red = 0
        self.car_blue_last_action = None
        self.car_red_last_action = None
        self.car_blue_track_timer = 0
        self.car_red_track_timer = 0
        self.menu_background = pygame.image.load("assets/menu_backround.png").convert()
        self.menu_items = ["Spieler 1", "Spieler 2", "Spieler 3", "Spieler 4", "Beenden"]
        self.menu_selected = 0
        self.game_timer = 120  # 2 Minuten in Sekunden
        self.game_start_time = None
        
        # Multithreading-Setup
        self.ai_queue = queue.Queue()
        self.tire_queue = queue.Queue()
        self.collision_queue = queue.Queue()
        self.ai_thread = None
        self.tire_thread = None
        self.collision_thread = None
        self.running = False
        self.spawnpoints = []  # Liste von Spawnpunkten für Autos

    def _load_and_scale(self, path, scale):
        surf = pygame.image.load(path).convert_alpha()
        w, h = surf.get_size()
        new_size = (int(w*scale), int(h*scale))
        return pygame.transform.smoothscale(surf, new_size)

    def load_field(self):
        field = pygame.image.load("assets/field.png").convert()
        return field

    def ai_thread_worker(self):
        """Separater Thread für KI-Berechnungen"""
        while self.running:
            try:
                # Warte auf AI-Aufgaben
                task = self.ai_queue.get(timeout=0.016)  # 60 FPS
                if task is None:  # Stop-Signal
                    break
                    
                car, ball, goals, teammates, opponents = task
                if isinstance(car, CarAI):
                    car.update_ai(ball, goals, teammates, opponents)
                    
                self.ai_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"AI Thread Error: {e}")
                continue

    def tire_thread_worker(self):
        """Separater Thread für Reifenspuren-Berechnungen"""
        while self.running:
            try:
                # Warte auf Reifenspuren-Aufgaben
                task = self.tire_queue.get(timeout=0.016)  # 60 FPS
                if task is None:  # Stop-Signal
                    break
                    
                car, action = task
                self.add_tire_tracks(car, action)
                    
                self.tire_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Tire Thread Error: {e}")
                continue

    def collision_thread_worker(self):
        """Separater Thread für Kollisionserkennung"""
        while self.running:
            try:
                # Warte auf Kollisions-Aufgaben
                task = self.collision_queue.get(timeout=0.016)  # 60 FPS
                if task is None:  # Stop-Signal
                    break
                    
                cars, ball, goals = task
                
                # Auto-zu-Auto Kollisionen mit Arcade-Physik
                for i, car1 in enumerate(cars):
                    for j, car2 in enumerate(cars):
                        if i >= j:
                            continue
                        # Nur schneller Bounding-Box-Check
                        if car1.rect.colliderect(car2.rect):
                            # Sanfte Arcade-Kollisionsphysik
                            direction = pygame.Vector2(car1.rect.center) - pygame.Vector2(car2.rect.center)
                            if direction.length() > 0:
                                direction = direction.normalize()
                                
                                # Schiebe Autos nur leicht auseinander
                                push_distance = 8
                                car1.position += direction * push_distance
                                car2.position -= direction * push_distance
                                car1.rect.center = (int(car1.position.x), int(car1.position.y))
                                car2.rect.center = (int(car2.position.x), int(car2.position.y))
                                
                                # Sanfte Arcade-Bounce: Leichte Geschwindigkeitsübertragung
                                car1_vel = pygame.Vector2(math.cos(math.radians(car1.angle)), math.sin(math.radians(car1.angle))) * car1.velocity
                                car2_vel = pygame.Vector2(math.cos(math.radians(car2.angle)), math.sin(math.radians(car2.angle))) * car2.velocity
                                
                                # Projektion der Geschwindigkeiten auf Kollisionsrichtung
                                car1_speed_in_direction = car1_vel.dot(direction)
                                car2_speed_in_direction = car2_vel.dot(direction)
                                
                                # Sanfte Bounce: Nur leichte Geschwindigkeitsübertragung
                                transfer_factor = 0.3  # Nur 30% der Geschwindigkeit wird übertragen
                                car1_speed_in_direction = car1_speed_in_direction * (1 - transfer_factor) + car2_speed_in_direction * transfer_factor
                                car2_speed_in_direction = car2_speed_in_direction * (1 - transfer_factor) + car1_speed_in_direction * transfer_factor
                                
                                # Berechne neue Geschwindigkeitsvektoren
                                car1_vel_perpendicular = car1_vel - direction * car1_vel.dot(direction)
                                car2_vel_perpendicular = car2_vel - direction * car2_vel.dot(direction)
                                
                                car1_new_vel = car1_vel_perpendicular + direction * car1_speed_in_direction
                                car2_new_vel = car2_vel_perpendicular + direction * car2_speed_in_direction
                                
                                # Wende neue Geschwindigkeiten an
                                car1.velocity = car1_new_vel.length()
                                car2.velocity = car2_new_vel.length()
                                
                                # Berechne neue Winkel (nur bei ausreichender Geschwindigkeit)
                                if car1.velocity > 0.5:
                                    car1.angle = math.degrees(math.atan2(car1_new_vel.y, car1_new_vel.x))
                                if car2.velocity > 0.5:
                                    car2.angle = math.degrees(math.atan2(car2_new_vel.y, car2_new_vel.x))
                                
                                # Sehr sanfte Geschwindigkeitsreduktion
                                car1.velocity *= 0.95
                                car2.velocity *= 0.95
                
                # Auto-zu-Pfosten Kollisionen
                for car in cars:
                    for post in goals.posts:
                        car_center = pygame.Vector2(car.rect.center)
                        dist = car_center.distance_to(post)
                        min_dist = goals.post_radius + car.rect.width//2 * 0.7
                        if dist < min_dist:
                            direction = car_center - pygame.Vector2(post)
                            if direction.length() == 0:
                                direction = pygame.Vector2(1,0)
                            direction = direction.normalize()
                            overlap = min_dist - dist
                            car.position += direction * overlap
                            car.rect.center = (int(car.position.x), int(car.position.y))
                            car.velocity *= -0.5
                
                # Ball-zu-Auto Kollisionen
                for car in cars:
                    ball_center = pygame.Vector2(ball.rect.center)
                    closest = closest_point_on_rotated_rect(ball_center, car)
                    dist = ball_center.distance_to(closest)
                    if dist < BALL_RADIUS:
                        direction = (ball_center - closest)
                        if direction.length() == 0:
                            direction = pygame.Vector2(1,0)
                        direction = direction.normalize()
                        overlap = BALL_RADIUS - dist
                        ball.pos += direction * overlap
                        ball.rect.center = (int(ball.pos.x), int(ball.pos.y))
                        v_norm = ball.vel.dot(direction)
                        if v_norm < 0:
                            ball.vel = ball.vel - direction * v_norm * 2
                        if car.velocity > 0:
                            ball.vel += direction * abs(car.velocity) * 1.2
                        else:
                            ball.vel += direction * 3
                        car.velocity *= 0.7
                        max_ball_speed = 8 * (self.WIDTH / 256)
                        if ball.vel.length() > max_ball_speed:
                            ball.vel.scale_to_length(max_ball_speed)
                
                # Ball-zu-Pfosten Kollisionen
                for post in goals.posts:
                    dist = pygame.Vector2(ball.rect.center).distance_to(post)
                    if dist < goals.post_radius + BALL_RADIUS:
                        direction = pygame.Vector2(ball.rect.center) - pygame.Vector2(post)
                        if direction.length() == 0:
                            direction = pygame.Vector2(1,0)
                        direction = direction.normalize()
                        ball.vel = direction * ball.vel.length() * 0.8
                        overlap = goals.post_radius + BALL_RADIUS - dist
                        ball.pos += direction * overlap
                        ball.rect.center = (int(ball.pos.x), int(ball.pos.y))
                    
                self.collision_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Collision Thread Error: {e}")
                continue

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
    def show_mode_menu(self, player_count):
        mode_items = ["Freunde", "KI"]
        mode_selected = 0
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        mode_selected = (mode_selected - 1) % len(mode_items)
                    if event.key == pygame.K_RIGHT:
                        mode_selected = (mode_selected + 1) % len(mode_items)
                    if event.key == pygame.K_RETURN:
                        return mode_items[mode_selected]
            self.screen.fill((0, 0, 0))
            self.screen.blit(pygame.transform.scale(self.menu_background, (self.WIDTH, self.HEIGHT)), (0, 0))
            menu_bar_height = 90
            menu_bar_rect = pygame.Rect(0, self.HEIGHT - menu_bar_height, self.WIDTH, menu_bar_height)
            pygame.draw.rect(self.screen, (0, 0, 0), menu_bar_rect)
            mode_surfs = [self.menu_font.render(item, True, (0,255,0) if i==mode_selected else (255,255,255)) for i,item in enumerate(mode_items)]
            total_width = sum(surf.get_width() for surf in mode_surfs) + (len(mode_surfs)-1)*60
            start_x = (self.WIDTH - total_width)//2
            y = self.HEIGHT - 60
            x = start_x
            for surf in mode_surfs:
                rect = surf.get_rect(midbottom=(x + surf.get_width()//2, y))
                self.screen.blit(surf, rect)
                x += surf.get_width() + 60
            by_font = pygame.font.SysFont("Courier New", 22, bold=True)
            by_text = by_font.render("By Superfliege", True, (200, 200, 200))
            by_rect = by_text.get_rect(bottomright=(self.WIDTH-18, self.HEIGHT-10))
            self.screen.blit(by_text, by_rect)
            pygame.display.flip()
            self.clock.tick(60)

    def show_connect_screen(self, player_count):
        # Keine Fehlermeldung mehr anzeigen, egal wie viele Spieler
        return

    def show_error_screen(self, message):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN or event.key == pygame.K_BACKSPACE:
                        return  # Zurück zum Hauptmenü
            self.screen.fill((30, 0, 0))
            font = pygame.font.SysFont("Arial", 48, bold=True)
            msg = font.render(message, True, (255, 80, 80))
            msg_rect = msg.get_rect(center=(self.WIDTH//2, self.HEIGHT//2 - 40))
            self.screen.blit(msg, msg_rect)
            btn_font = pygame.font.SysFont("Arial", 36, bold=True)
            btn = btn_font.render("Zurück (ESC/Enter/Backspace)", True, (255,255,255))
            btn_rect = btn.get_rect(center=(self.WIDTH//2, self.HEIGHT//2 + 40))
            self.screen.blit(btn, btn_rect)
            pygame.display.flip()
            self.clock.tick(30)

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
                            player_count = self.menu_selected + 1
                            # Nur bei 2, 3, 4 Spielern Modus-Auswahl
                            if player_count == 1:
                                return player_count, "Solo"
                            else:
                                mode = self.show_mode_menu(player_count)
                                return player_count, mode
            self.screen.fill((0, 0, 0))
            self.screen.blit(pygame.transform.scale(self.menu_background, (self.WIDTH, self.HEIGHT)), (0, 0))
            menu_bar_height = 90
            menu_bar_rect = pygame.Rect(0, self.HEIGHT - menu_bar_height, self.WIDTH, menu_bar_height)
            pygame.draw.rect(self.screen, (0, 0, 0), menu_bar_rect)
            menu_surfs = [self.menu_font.render(item, True, (0,255,0) if i==self.menu_selected else (255,255,255)) for i,item in enumerate(self.menu_items)]
            total_width = sum(surf.get_width() for surf in menu_surfs) + (len(menu_surfs)-1)*60
            start_x = (self.WIDTH - total_width)//2
            y = self.HEIGHT - 60
            x = start_x
            for surf in menu_surfs:
                rect = surf.get_rect(midbottom=(x + surf.get_width()//2, y))
                self.screen.blit(surf, rect)
                x += surf.get_width() + 60
            by_font = pygame.font.SysFont("Courier New", 22, bold=True)
            by_text = by_font.render("By Superfliege", True, (200, 200, 200))
            by_rect = by_text.get_rect(bottomright=(self.WIDTH-18, self.HEIGHT-10))
            self.screen.blit(by_text, by_rect)
            pygame.display.flip()
            self.clock.tick(60)

    def run(self):
        player_count, mode = self.show_menu()
        if mode == "Solo":
            # Nur ein Spieler, kein KI-Gegner
            self.running = True
            self.ai_thread = threading.Thread(target=self.ai_thread_worker, daemon=True)
            self.tire_thread = threading.Thread(target=self.tire_thread_worker, daemon=True)
            self.collision_thread = threading.Thread(target=self.collision_thread_worker, daemon=True)
            self.ai_thread.start()
            self.tire_thread.start()
            self.collision_thread.start()
            car_imgs = [self.img_red]
            left_x = 120
            center_y = self.HEIGHT//2
            self.cars = []
            self.cars.append(Auto(car_imgs[0], left_x, center_y, 2.0, (self.WIDTH, self.HEIGHT)))
            self.cars[0].angle = 0
            # Nach dem Erstellen der Autos:
            self.spawnpoints = [(car.position.x, car.position.y, car.angle) for car in self.cars]
            # --- Game-Loop wie gehabt ---
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                now = time.time()
                if self.game_start_time is None:
                    self.game_start_time = now
                elapsed_time = now - self.game_start_time
                remaining_time = max(0, self.game_timer - elapsed_time)
                if remaining_time <= 0:
                    self.show_final_score()
                    self.running = False
                    self.ai_queue.put(None)
                    self.tire_queue.put(None)
                    self.collision_queue.put(None)
                    if self.ai_thread:
                        self.ai_thread.join(timeout=1.0)
                    if self.tire_thread:
                        self.tire_thread.join(timeout=1.0)
                    if self.collision_thread:
                        self.collision_thread.join(timeout=1.0)
                    return
                self.ball.update()
                try:
                    self.collision_queue.put_nowait((self.cars, self.ball, self.goals))
                except queue.Full:
                    pass
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
                # Steuerung für Spieler 1 (WASD)
                keys = pygame.key.get_pressed()
                now = time.time()
                if not hasattr(self, 'car_prev_vels'):
                    self.car_prev_vels = {}
                # Für alle Autos (egal ob Mensch oder KI)
                for i, car in enumerate(self.cars):
                    prev_vel = self.car_prev_vels.get(i, 0)
                    # Steuerung für Menschen
                    if i == 0:
                        if keys[pygame.K_w]:
                            car.accelerate()
                        elif keys[pygame.K_s]:
                            car.reverse()
                        if keys[pygame.K_a]:
                            car.steer_left()
                        if keys[pygame.K_d]:
                            car.steer_right()
                        # Drift (NumPad 0, Shift oder Space), nur bei Geschwindigkeit
                        if (keys[pygame.K_KP0] or keys[pygame.K_LSHIFT] or keys[pygame.K_SPACE]) and abs(car.velocity) > 1.0:
                            car.drift()
                    elif i == 1:
                        if keys[pygame.K_UP]:
                            car.accelerate()
                        elif keys[pygame.K_DOWN]:
                            car.reverse()
                        if keys[pygame.K_LEFT]:
                            car.steer_left()
                        if keys[pygame.K_RIGHT]:
                            car.steer_right()
                        if (keys[pygame.K_KP0] or keys[pygame.K_RSHIFT] or keys[pygame.K_RCTRL]) and abs(car.velocity) > 1.0:
                            car.drift()
                    # KI-Autos werden wie gehabt durch update_ai gesteuert (bereits im Thread)
                    car.update()
                    # Reifenspuren-Logik: Nur beim Übergang Beschleunigen oder Bremsen, einmalig
                    if prev_vel < 0.5 and abs(car.velocity) > 1.0:
                        try:
                            self.tire_queue.put_nowait((car, 'gas'))
                        except queue.Full:
                            pass
                    elif prev_vel > 1.0 and abs(car.velocity) < 0.5:
                        try:
                            self.tire_queue.put_nowait((car, 'brake'))
                        except queue.Full:
                            pass
                    self.car_prev_vels[i] = abs(car.velocity)
        elif mode == "Freunde":
            self.show_connect_screen(player_count)
            if player_count > 4:
                return  # Nach Fehlermeldung zurück ins Menü
            self.running = True
            self.ai_thread = threading.Thread(target=self.ai_thread_worker, daemon=True)
            self.tire_thread = threading.Thread(target=self.tire_thread_worker, daemon=True)
            self.collision_thread = threading.Thread(target=self.collision_thread_worker, daemon=True)
            self.ai_thread.start()
            self.tire_thread.start()
            self.collision_thread.start()
            car_imgs = [self.img_red, self.img_blue, self.img_yellow, self.img_pink]
            left_x = 120
            right_x = self.WIDTH-120
            center_y = self.HEIGHT//2
            top_y = 220
            bottom_y = self.HEIGHT-220
            self.cars = []
            if player_count == 2:
                # 2 Menschen + 1 KI-Gegner
                self.cars.append(Auto(car_imgs[0], left_x, center_y, 2.0, (self.WIDTH, self.HEIGHT)))
                self.cars[0].angle = 0
                self.cars.append(Auto(car_imgs[1], right_x, center_y, 2.0, (self.WIDTH, self.HEIGHT)))
                self.cars[1].angle = 180
                self.cars.append(CarAI(car_imgs[2], right_x, top_y, 2.0, (self.WIDTH, self.HEIGHT), team='yellow', side='right'))
                self.cars[2].angle = 180
            elif player_count == 3:
                # 2 Menschen + 1 KI-Gegner
                self.cars.append(Auto(car_imgs[0], left_x, center_y, 2.0, (self.WIDTH, self.HEIGHT)))
                self.cars[0].angle = 0
                self.cars.append(Auto(car_imgs[1], right_x, center_y, 2.0, (self.WIDTH, self.HEIGHT)))
                self.cars[1].angle = 180
                self.cars.append(CarAI(car_imgs[2], right_x, top_y, 2.0, (self.WIDTH, self.HEIGHT), team='yellow', side='right'))
                self.cars[2].angle = 180
            elif player_count == 4:
                # 2 Menschen + 2 KI-Gegner
                self.cars.append(Auto(car_imgs[0], left_x, top_y, 2.0, (self.WIDTH, self.HEIGHT)))
                self.cars[0].angle = 0
                self.cars.append(Auto(car_imgs[1], left_x, bottom_y, 2.0, (self.WIDTH, self.HEIGHT)))
                self.cars[1].angle = 0
                self.cars.append(CarAI(car_imgs[2], right_x, top_y, 2.0, (self.WIDTH, self.HEIGHT), team='yellow', side='right'))
                self.cars[2].angle = 180
                self.cars.append(CarAI(car_imgs[3], right_x, bottom_y, 2.0, (self.WIDTH, self.HEIGHT), team='pink', side='right'))
                self.cars[3].angle = 180
            # Nach dem Erstellen der Autos:
            self.spawnpoints = [(car.position.x, car.position.y, car.angle) for car in self.cars]
            # --- Game-Loop wie gehabt ---
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                now = time.time()
                if self.game_start_time is None:
                    self.game_start_time = now
                elapsed_time = now - self.game_start_time
                remaining_time = max(0, self.game_timer - elapsed_time)
                if remaining_time <= 0:
                    self.show_final_score()
                    self.running = False
                    self.ai_queue.put(None)
                    self.tire_queue.put(None)
                    self.collision_queue.put(None)
                    if self.ai_thread:
                        self.ai_thread.join(timeout=1.0)
                    if self.tire_thread:
                        self.tire_thread.join(timeout=1.0)
                    if self.collision_thread:
                        self.collision_thread.join(timeout=1.0)
                    return
                # KI-Logik für CarAI (wie gehabt)
                for i, car in enumerate(self.cars[2:], start=2):
                    prev_vel_ai = car.velocity
                    if isinstance(car, CarAI):
                        teammates = [c for c in self.cars if c is not car and getattr(c, 'team', None) == car.team]
                        opponents = [c for c in self.cars if c is not car and getattr(c, 'team', None) != car.team]
                        try:
                            self.ai_queue.put_nowait((car, self.ball, self.goals, teammates, opponents))
                        except queue.Full:
                            pass
                    else:
                        car.update()
                    # Reifenspuren-Logik wie gehabt ...
                    if prev_vel_ai < 0.5 and car.velocity >= 0.5:
                        if not hasattr(self, 'car_track_timers'):
                            self.car_track_timers = {}
                        self.car_track_timers[i] = now + TRACK_MARK_TIME
                    if car.velocity > 0.5 and car.velocity > prev_vel_ai * 1.1:
                        if not hasattr(self, 'car_accel_timers'):
                            self.car_accel_timers = {}
                        self.car_accel_timers[i] = now + 0.3
                    if hasattr(self, 'car_track_timers') and i in self.car_track_timers and self.car_track_timers[i] > now:
                        if car.velocity > 0:
                            try:
                                self.tire_queue.put_nowait((car, 'gas'))
                            except queue.Full:
                                pass
                        elif car.velocity < 0:
                            try:
                                self.tire_queue.put_nowait((car, 'brake'))
                            except queue.Full:
                                pass
                    if hasattr(self, 'car_accel_timers') and i in self.car_accel_timers and self.car_accel_timers[i] > now:
                        if car.velocity > 0:
                            try:
                                self.tire_queue.put_nowait((car, 'accel'))
                            except queue.Full:
                                pass
                self.ball.update()
                try:
                    self.collision_queue.put_nowait((self.cars, self.ball, self.goals))
                except queue.Full:
                    pass
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
                # Steuerung für Spieler 1 (WASD)
                keys = pygame.key.get_pressed()
                now = time.time()
                if not hasattr(self, 'car_prev_vels'):
                    self.car_prev_vels = {}
                if not hasattr(self, 'car_accel_timers'):
                    self.car_accel_timers = {}
                if not hasattr(self, 'car_brake_timers'):
                    self.car_brake_timers = {}
                # Für alle Autos (egal ob Mensch oder KI)
                for i, car in enumerate(self.cars):
                    prev_vel = self.car_prev_vels.get(i, 0)
                    # Steuerung für Menschen
                    if i == 0:
                        if keys[pygame.K_w]:
                            car.accelerate()
                        elif keys[pygame.K_s]:
                            car.reverse()
                        if keys[pygame.K_a]:
                            car.steer_left()
                        if keys[pygame.K_d]:
                            car.steer_right()
                        if (keys[pygame.K_KP0] or keys[pygame.K_LSHIFT] or keys[pygame.K_SPACE]) and abs(car.velocity) > 1.0:
                            car.drift()
                    elif i == 1:
                        if keys[pygame.K_UP]:
                            car.accelerate()
                        elif keys[pygame.K_DOWN]:
                            car.reverse()
                        if keys[pygame.K_LEFT]:
                            car.steer_left()
                        if keys[pygame.K_RIGHT]:
                            car.steer_right()
                        if (keys[pygame.K_KP0] or keys[pygame.K_RSHIFT] or keys[pygame.K_RCTRL]) and abs(car.velocity) > 1.0:
                            car.drift()
                    # KI-Autos werden wie gehabt durch update_ai gesteuert (bereits im Thread)
                    car.update()
                    # --- Reifenspuren-Logik ---
                    # Beschleunigen aus dem Stand: Timer für 0.5 Sekunden, Spurtyp 'accel'
                    if prev_vel < 0.5 and abs(car.velocity) > 0.5:
                        self.car_accel_timers[i] = now + 0.5
                    # Bremsen: Timer für 0.5 Sekunden, Spurtyp 'brake'
                    if prev_vel > 1.0 and abs(car.velocity) < 0.5:
                        self.car_brake_timers[i] = now + 0.5
                    # Solange Timer läuft, Reifenspuren zeichnen
                    if i in self.car_accel_timers and self.car_accel_timers[i] > now:
                        try:
                            self.tire_queue.put_nowait((car, 'accel'))
                        except queue.Full:
                            pass
                    if i in self.car_brake_timers and self.car_brake_timers[i] > now:
                        try:
                            self.tire_queue.put_nowait((car, 'brake'))
                        except queue.Full:
                            pass
                    self.car_prev_vels[i] = abs(car.velocity)
        elif mode == "KI":
            self.running = True
            self.ai_thread = threading.Thread(target=self.ai_thread_worker, daemon=True)
            self.tire_thread = threading.Thread(target=self.tire_thread_worker, daemon=True)
            self.collision_thread = threading.Thread(target=self.collision_thread_worker, daemon=True)
            self.ai_thread.start()
            self.tire_thread.start()
            self.collision_thread.start()
            car_imgs = [self.img_red, self.img_blue, self.img_yellow, self.img_pink]
            left_x = 120
            right_x = self.WIDTH-120
            center_y = self.HEIGHT//2
            top_y = 220
            bottom_y = self.HEIGHT-220
            self.cars = []
            if player_count == 1:
                # Solo: Nur ein Spieler
                self.cars.append(Auto(car_imgs[0], left_x, center_y, 2.0, (self.WIDTH, self.HEIGHT)))
                self.cars[0].angle = 0
                # Gleiche Geschwindigkeit für alle Autos (Standardeinstellungen aus Auto werden verwendet)
            elif player_count == 2:
                # 1 Mensch, 1 KI-Gegner
                self.cars.append(Auto(car_imgs[0], left_x, center_y, 2.0, (self.WIDTH, self.HEIGHT)))
                self.cars[0].angle = 0
                self.cars.append(CarAI(car_imgs[1], right_x, center_y, 2.0, (self.WIDTH, self.HEIGHT), team='blue', side='right'))
                self.cars[1].angle = 180
                # Gleiche Geschwindigkeit für alle Autos (Standardeinstellungen aus Auto werden verwendet)
            elif player_count == 3:
                # 1 Mensch, 2 KI-Gegner
                self.cars.append(Auto(car_imgs[0], left_x, center_y, 2.0, (self.WIDTH, self.HEIGHT)))
                self.cars[0].angle = 0
                self.cars.append(CarAI(car_imgs[1], right_x, top_y, 2.0, (self.WIDTH, self.HEIGHT), team='blue', side='right'))
                self.cars[1].angle = 180
                self.cars.append(CarAI(car_imgs[2], right_x, bottom_y, 2.0, (self.WIDTH, self.HEIGHT), team='yellow', side='right'))
                self.cars[2].angle = 180
                # Gleiche Geschwindigkeit für alle Autos (Standardeinstellungen aus Auto werden verwendet)
            elif player_count == 4:
                # 1 Mensch, 1 KI-Mitspieler, 2 KI-Gegner
                self.cars.append(Auto(car_imgs[0], left_x, top_y, 2.0, (self.WIDTH, self.HEIGHT)))
                self.cars[0].angle = 0
                self.cars.append(CarAI(car_imgs[1], left_x, bottom_y, 2.0, (self.WIDTH, self.HEIGHT), team='blue', side='left'))
                self.cars[1].angle = 0
                self.cars.append(CarAI(car_imgs[2], right_x, top_y, 2.0, (self.WIDTH, self.HEIGHT), team='yellow', side='right'))
                self.cars[2].angle = 180
                self.cars.append(CarAI(car_imgs[3], right_x, bottom_y, 2.0, (self.WIDTH, self.HEIGHT), team='pink', side='right'))
                self.cars[3].angle = 180
                # Gleiche Geschwindigkeit für alle Autos (Standardeinstellungen aus Auto werden verwendet)
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                now = time.time()
                if self.game_start_time is None:
                    self.game_start_time = now
                elapsed_time = now - self.game_start_time
                remaining_time = max(0, self.game_timer - elapsed_time)
                if remaining_time <= 0:
                    self.show_final_score()
                    self.running = False
                    self.ai_queue.put(None)
                    self.tire_queue.put(None)
                    self.collision_queue.put(None)
                    if self.ai_thread:
                        self.ai_thread.join(timeout=1.0)
                    if self.tire_thread:
                        self.tire_thread.join(timeout=1.0)
                    if self.collision_thread:
                        self.collision_thread.join(timeout=1.0)
                    return
                # KI-Logik für CarAI (wie gehabt)
                for i, car in enumerate(self.cars[1:], start=1):
                    prev_vel_ai = car.velocity
                    if isinstance(car, CarAI):
                        teammates = [c for c in self.cars if c is not car and getattr(c, 'team', None) == car.team]
                        opponents = [c for c in self.cars if c is not car and getattr(c, 'team', None) != car.team]
                        try:
                            self.ai_queue.put_nowait((car, self.ball, self.goals, teammates, opponents))
                        except queue.Full:
                            pass
                    else:
                        car.update()
                    # Reifenspuren-Logik wie gehabt ...
                    if prev_vel_ai < 0.5 and car.velocity >= 0.5:
                        if not hasattr(self, 'car_track_timers'):
                            self.car_track_timers = {}
                        self.car_track_timers[i] = now + TRACK_MARK_TIME
                    if car.velocity > 0.5 and car.velocity > prev_vel_ai * 1.1:
                        if not hasattr(self, 'car_accel_timers'):
                            self.car_accel_timers = {}
                        self.car_accel_timers[i] = now + 0.3
                    if hasattr(self, 'car_track_timers') and i in self.car_track_timers and self.car_track_timers[i] > now:
                        if car.velocity > 0:
                            try:
                                self.tire_queue.put_nowait((car, 'gas'))
                            except queue.Full:
                                pass
                        elif car.velocity < 0:
                            try:
                                self.tire_queue.put_nowait((car, 'brake'))
                            except queue.Full:
                                pass
                    if hasattr(self, 'car_accel_timers') and i in self.car_accel_timers and self.car_accel_timers[i] > now:
                        if car.velocity > 0:
                            try:
                                self.tire_queue.put_nowait((car, 'accel'))
                            except queue.Full:
                                pass
                self.ball.update()
                try:
                    self.collision_queue.put_nowait((self.cars, self.ball, self.goals))
                except queue.Full:
                    pass
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
                # Steuerung für Spieler 1 (WASD)
                keys = pygame.key.get_pressed()
                now = time.time()
                if not hasattr(self, 'car_prev_vels'):
                    self.car_prev_vels = {}
                if not hasattr(self, 'car_accel_timers'):
                    self.car_accel_timers = {}
                if not hasattr(self, 'car_brake_timers'):
                    self.car_brake_timers = {}
                # Für alle Autos (egal ob Mensch oder KI)
                for i, car in enumerate(self.cars):
                    prev_vel = self.car_prev_vels.get(i, 0)
                    # Steuerung für Menschen
                    if i == 0:
                        if keys[pygame.K_w]:
                            car.accelerate()
                        elif keys[pygame.K_s]:
                            car.reverse()
                        else:
                            car.brake()
                        if keys[pygame.K_a]:
                            car.steer_left()
                        if keys[pygame.K_d]:
                            car.steer_right()
                    elif i == 1:
                        if keys[pygame.K_UP]:
                            car.accelerate()
                        elif keys[pygame.K_DOWN]:
                            car.reverse()
                        else:
                            car.brake()
                        if keys[pygame.K_LEFT]:
                            car.steer_left()
                        if keys[pygame.K_RIGHT]:
                            car.steer_right()
                    # KI-Autos werden wie gehabt durch update_ai gesteuert (bereits im Thread)
                    car.update()
                    # --- Reifenspuren-Logik ---
                    # Beschleunigen aus dem Stand: Timer für 1 Sekunde, Spurtyp 'accel'
                    if prev_vel < 0.5 and abs(car.velocity) > 0.5:
                        self.car_accel_timers[i] = now + 1.0
                    # Bremsen: Timer für 1 Sekunde, Spurtyp 'brake'
                    if prev_vel > 1.0 and abs(car.velocity) < 0.5:
                        self.car_brake_timers[i] = now + 1.0
                    # Solange Timer läuft, Reifenspuren zeichnen
                    if i in self.car_accel_timers and self.car_accel_timers[i] > now:
                        try:
                            self.tire_queue.put_nowait((car, 'accel'))
                        except queue.Full:
                            pass
                    if i in self.car_brake_timers and self.car_brake_timers[i] > now:
                        try:
                            self.tire_queue.put_nowait((car, 'brake'))
                        except queue.Full:
                            pass
                    self.car_prev_vels[i] = abs(car.velocity)

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
        # Countdown-Anzeige
        if remaining_time > 10:
            minutes = int(remaining_time) // 60
            seconds = int(remaining_time) % 60
            countdown_text = self.font.render(f"{minutes:02d}:{seconds:02d}", True, (255, 255, 255))
            countdown_rect = countdown_text.get_rect(topright=(self.WIDTH - 20, 20))
            self.screen.blit(countdown_text, countdown_rect)
        else:
            # Großer, halbtransparenter, roter Timer mittig oben
            big_font = pygame.font.SysFont("Arial", 120, bold=True)
            seconds = int(remaining_time)
            big_timer_text = big_font.render(f"{seconds}", True, (255, 0, 0))
            # Transparenter Hintergrundbalken
            overlay = pygame.Surface((self.WIDTH, 160), pygame.SRCALPHA)
            overlay.fill((255, 0, 0, 80))  # Rot, halbtransparent
            self.screen.blit(overlay, (0, 0))
            timer_rect = big_timer_text.get_rect(midtop=(self.WIDTH//2, 10))
            self.screen.blit(big_timer_text, timer_rect)
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