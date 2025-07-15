import pygame
import math
import time
import random
from collections import deque
from auto import Auto

class CarAI(Auto):
    def __init__(self, *args, team='red', side='left', **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        self.side = side  # 'left' oder 'right'
        self.last_active_time = time.time()
        self.collision_timer = {}  # key: id(other), value: {'start': t, 'end': t or None}
        self.unstuck_until = 0  # Zeit bis zu der die KI gezielt ausweicht
        self.unstuck_dir = 0    # -1 = links, 1 = rechts
        self.pos_history = deque(maxlen=30)  # ca. 0.5s bei 60 FPS
        self.random_offset = random.uniform(-20, 20)  # initialer Offset
        self.last_offset_update = time.time()

    def update_ai(self, ball, goals, teammates, opponents):
        if self.side == 'left':
            own_goal = pygame.Vector2(goals.left1)
            target_goal = pygame.Vector2(goals.right1)
        else:
            own_goal = pygame.Vector2(goals.right1)
            target_goal = pygame.Vector2(goals.left1)
        ball_vec = pygame.Vector2(ball.pos)
        car_vec = self.position
        shot_dir = (target_goal - ball_vec).normalize()
        # --- S-förmiger Offset: alle 1.0s neu wählen, Vorzeichen wechselt ab, Amplitude bis 80px ---
        now = time.time()
        if not hasattr(self, 'offset_sign'):
            self.offset_sign = 1
        if now - self.last_offset_update > 1.0:
            self.random_offset = self.offset_sign * random.uniform(40, 80)
            self.offset_sign *= -1
            self.last_offset_update = now
        ortho = pygame.Vector2(-shot_dir.y, shot_dir.x)
        behind_ball = ball_vec - shot_dir * 80 + ortho * self.random_offset
        far_behind_ball = ball_vec - shot_dir * 200 + ortho * self.random_offset

        # --- Positionshistorie für stuck detection ---
        self.pos_history.append(pygame.Vector2(self.position))
        stuck = False
        stuck_distance = 5  # px
        stuck_velocity = 0.2
        if len(self.pos_history) == self.pos_history.maxlen:
            dist_moved = (self.pos_history[-1] - self.pos_history[0]).length()
            if dist_moved < stuck_distance and abs(self.velocity) < stuck_velocity:
                stuck = True

        # Unstuck-Phase: gezielt zur Seite fahren
        if now < self.unstuck_until:
            ortho_unstuck = pygame.Vector2(-shot_dir.y, shot_dir.x) * self.unstuck_dir
            unstuck_target = car_vec + ortho_unstuck * 60
            self._drive_to(unstuck_target)
            super().update()
            self._update_activity()
            return

        # Kollisionsvermeidung: Abstand zu anderen Autos prüfen
        min_dist = 10
        collision = False
        for other in teammates + opponents:
            if other is self:
                continue
            other_vec = getattr(other, 'position', None)
            if other_vec is not None:
                dist = (car_vec - other_vec).length()
                oid = id(other)
                # Enger Kontakt
                if dist < min_dist:
                    collision = True
                    if oid not in self.collision_timer or self.collision_timer[oid]['end'] is not None:
                        self.collision_timer[oid] = {'start': now, 'end': None}
                    # Prüfe, ob stuck: stuck + collision + velocity
                    if stuck:
                        rel_vec = other_vec - car_vec
                        forward = pygame.Vector2(math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle)))
                        cross = forward.x * rel_vec.y - forward.y * rel_vec.x
                        if cross > 0:
                            self.unstuck_dir = -1  # links
                        else:
                            self.unstuck_dir = 1   # rechts
                        self.unstuck_until = now + 5.0
                        self.collision_timer[oid]['start'] = now
                else:
                    if oid in self.collision_timer and self.collision_timer[oid]['end'] is None:
                        self.collision_timer[oid]['end'] = now
                    elif oid in self.collision_timer and self.collision_timer[oid]['end'] is not None:
                        if now - self.collision_timer[oid]['end'] > 0.2:
                            del self.collision_timer[oid]

        # Defensive: Ball nahe am eigenen Tor?
        if (ball_vec - own_goal).length() < 220:
            defend_point = ball_vec + (ball_vec - own_goal).normalize() * 60
            self._drive_to(defend_point)
            super().update()
            self._update_activity()
            return

        car_to_ball = (ball_vec - car_vec).normalize()
        ball_to_goal = (target_goal - ball_vec).normalize()
        alignment = car_to_ball.dot(ball_to_goal)
        dist_car_ball = (car_vec - ball_vec).length()

        # Fallback: Wenn Velocity zu lange zu klein, fahre weit hinter den Ball
        if abs(self.velocity) < 0.1:
            if time.time() - self.last_active_time > 2.0:
                self._drive_to(far_behind_ball)
                super().update()
                return
        else:
            self._update_activity()

        # Wenn Ball hinter der KI: weiter hinter den Ball fahren (Bogen)
        if alignment < 0:
            self._drive_to(far_behind_ball)
        # Wenn gut ausgerichtet und nah am Ball: Schuss!
        elif alignment > 0.85 and dist_car_ball < 120:
            shot_point = ball_vec + shot_dir * 40
            self._drive_to(shot_point, boost=True)
        else:
            self._drive_to(behind_ball)
        super().update()

    def _drive_to(self, target, boost=False):
        car_vec = self.position
        target_angle = math.degrees(math.atan2((target - car_vec).y, (target - car_vec).x))
        angle_diff = (target_angle - self.angle + 360) % 360
        if angle_diff > 180:
            angle_diff -= 360
        # Wenn Geschwindigkeit zu gering, immer beschleunigen
        if abs(self.velocity) <= 0.1:
            self.accelerate()
            return
        if abs(angle_diff) > 5:
            if angle_diff > 0:
                self.steer_right()
            else:
                self.steer_left()
        if abs(angle_diff) < 60:
            self.accelerate()
            if boost:
                self.accelerate()
                self.accelerate()
        else:
            self.brake()
        if abs(angle_diff) > 60:
            self.drift()

    def _update_activity(self):
        if abs(self.velocity) > 0.1:
            self.last_active_time = time.time() 