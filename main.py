# endless_runner_panda3d.py
# Cartoon-ish endless runner prototype using Panda3D
# Controls: Left/Right = change lane, Space = jump, R = restart, Esc = quit

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    Vec3, Vec4, Point3, DirectionalLight, AmbientLight,
    CollisionTraverser, CollisionHandlerQueue, CollisionNode, CollisionBox,
    BitMask32, TextNode
)
from direct.gui.OnscreenText import OnscreenText
from direct.task import Task
import random
import math

LANES = [-2.2, 0.0, 2.2]

class RunnerGame(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(0.75, 0.9, 1.0, 1)

        # Game state
        self.speed = 12.0
        self.speed_inc = 0.25
        self.distance = 0.0
        self.score = 0
        self.game_over = False
        self.target_lane = 1
        self.current_lane = 1
        self.lane_lerp = 15.0

        # Jump physics
        self.y_pos = 0.0
        self.z = 0.9
        self.vz = 0.0
        self.gravity = -32.0
        self.jump_vel = 14.0
        self.grounded = True

        # Setup
        self._setup_lights()
        self._setup_camera()
        self._setup_ui()
        self._setup_collisions()
        self._build_world()
        self._spawn_initial_obstacles()

        # Input
        self.accept('arrow_left', self._lane_left)
        self.accept('arrow_right', self._lane_right)
        self.accept('space', self._jump)
        self.accept('r', self._restart)
        self.accept('escape', self.userExit)

        self.taskMgr.add(self._update, 'update')

    def _setup_lights(self):
        dlight = DirectionalLight('dlight')
        dlight.setColor(Vec4(1, 1, 1, 1))
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(-35, -55, 0)
        self.render.setLight(dlnp)

        alight = AmbientLight('alight')
        alight.setColor(Vec4(0.35, 0.35, 0.42, 1))
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)

    def _setup_camera(self):
        self.camera.setPos(0, -18, 6.5)
        self.camera.setHpr(0, -12, 0)

    def _setup_ui(self):
        self.txt = OnscreenText(
            text='Score: 0',
            pos=(-1.32, 0.92),
            scale=0.06,
            fg=(0.08, 0.08, 0.12, 1),
            align=TextNode.ALeft
        )
        self.txt2 = OnscreenText(
            text='',
            pos=(0, 0.0),
            scale=0.08,
            fg=(0.1, 0.1, 0.15, 1),
            align=TextNode.ACenter
        )

    def _setup_collisions(self):
        self.cTrav = CollisionTraverser('trav')
        self.cQueue = CollisionHandlerQueue()

        self.player_cnode = CollisionNode('player')
        self.player_cnode.addSolid(CollisionBox(Point3(0, 0, 1.0), 0.55, 0.55, 0.95))
        self.player_cnode.setFromCollideMask(BitMask32.bit(1))
        self.player_cnode.setIntoCollideMask(BitMask32.allOff())
        self.player_cnp = self.render.attachNewNode(self.player_cnode)

        self.cTrav.addCollider(self.player_cnp, self.cQueue)

    def _build_world(self):
        # Ground segments
        self.ground_root = self.render.attachNewNode('ground_root')
        self.ground_segments = []
        seg_len = 20.0
        self.seg_len = seg_len
        for i in range(8):
            seg = self.loader.loadModel('models/box')
            seg.reparentTo(self.ground_root)
            seg.setScale(7.2, seg_len, 0.25)
            seg.setPos(0, i * seg_len, -0.25)
            seg.setColor(0.25, 0.75, 0.35, 1)  # cartoon green
            self.ground_segments.append(seg)

        # Side walls (visual)
        self.side_root = self.render.attachNewNode('sides')
        for side in (-1, 1):
            wall = self.loader.loadModel('models/box')
            wall.reparentTo(self.side_root)
            wall.setScale(0.35, 200, 2.2)
            wall.setPos(side * 4.1, 70, 1.2)
            wall.setColor(0.92, 0.55, 0.2, 1)  # cartoon orange

        # Player (cartoon capsule-ish)
        self.player = self.render.attachNewNode('player_np')
        body = self.loader.loadModel('models/box')
        body.reparentTo(self.player)
        body.setScale(0.75, 0.75, 1.2)
        body.setPos(0, 0, 1.1)
        body.setColor(0.2, 0.45, 0.95, 1)

        head = self.loader.loadModel('models/box')
        head.reparentTo(self.player)
        head.setScale(0.55, 0.55, 0.55)
        head.setPos(0, 0, 2.1)
        head.setColor(1.0, 0.85, 0.65, 1)

        self.player.setPos(LANES[self.current_lane], self.y_pos, 0)
        self.player_cnp.reparentTo(self.player)
        self.player_cnp.setPos(0, 0, 0)

        # Obstacle root
        self.obstacles_np = self.render.attachNewNode('obstacles')
        self.obstacles = []

        # Sky deco
        for i in range(10):
            cloud = self.loader.loadModel('models/box')
            cloud.reparentTo(self.render)
            cloud.setScale(random.uniform(1.5, 3.2), random.uniform(2.5, 5.5), random.uniform(0.4, 0.9))
            cloud.setPos(random.uniform(-14, 14), random.uniform(5, 160), random.uniform(8, 14))
            cloud.setColor(1, 1, 1, 0.9)

    def _spawn_obstacle(self, y):
        lane = random.randint(0, 2)
        height_type = random.random()
        if height_type < 0.25:
            # jump obstacle (low wall)
            z = 0.55
            sz = 0.6
            sy = 0.7
        else:
            # tall box
            z = 0.9
            sz = 1.0
            sy = 0.8

        obs = self.loader.loadModel('models/box')
        obs.reparentTo(self.obstacles_np)
        obs.setScale(0.9, sy, sz)
        obs.setPos(LANES[lane], y, z)
        obs.setColor(0.95, 0.25, 0.35, 1)

        cnode = CollisionNode('obstacle')
        cnode.addSolid(CollisionBox(Point3(0, 0, 0), 0.55, 0.55, 0.7))
        cnode.setIntoCollideMask(BitMask32.bit(1))
        cnode.setFromCollideMask(BitMask32.allOff())
        cnp = obs.attachNewNode(cnode)

        self.obstacles.append((obs, cnp, lane))

    def _spawn_initial_obstacles(self):
        y = 28.0
        for _ in range(14):
            self._spawn_obstacle(y)
            y += random.uniform(8.0, 13.0)

    def _lane_left(self):
        if self.game_over:
            return
        self.target_lane = max(0, self.target_lane - 1)

    def _lane_right(self):
        if self.game_over:
            return
        self.target_lane = min(2, self.target_lane + 1)

    def _jump(self):
        if self.game_over:
            return
        if self.grounded:
            self.vz = self.jump_vel
            self.grounded = False

    def _restart(self):
        # reset state
        self.speed = 12.0
        self.distance = 0.0
        self.score = 0
        self.game_over = False
        self.target_lane = 1
        self.current_lane = 1
        self.y_pos = 0.0
        self.z = 0.9
        self.vz = 0.0
        self.grounded = True
        self.player.setPos(LANES[self.current_lane], self.y_pos, 0)
        self.txt2.setText('')

        # clear obstacles
        for obs, _, _ in self.obstacles:
            obs.removeNode()
        self.obstacles.clear()
        self._spawn_initial_obstacles()

    def _update(self, task: Task):
        dt = globalClock.getDt()
        if dt > 0.05:
            dt = 0.05

        if not self.game_over:
            # Move world towards player
            dy = self.speed * dt
            self.distance += dy

            # Increase speed a bit
            self.speed += self.speed_inc * dt

            # Lerp lane
            desired_x = LANES[self.target_lane]
            x = self.player.getX()
            x = x + (desired_x - x) * min(1.0, self.lane_lerp * dt)
            self.player.setX(x)

            # Jump physics
            self.vz += self.gravity * dt
            self.z += self.vz * dt
            if self.z <= 0.9:
                self.z = 0.9
                self.vz = 0.0
                self.grounded = True
            self.player.setZ(self.z - 0.9)  # player node at ground

            # Scroll ground
            for seg in self.ground_segments:
                seg.setY(seg.getY() - dy)
                if seg.getY() < -self.seg_len:
                    seg.setY(seg.getY() + self.seg_len * len(self.ground_segments))

            # Move obstacles
            recycle_y = 0
            max_y = max([o.getY() for o, _, _ in self.obstacles], default=60.0)
            for i, (obs, cnp, lane) in enumerate(list(self.obstacles)):
                obs.setY(obs.getY() - dy)
                if obs.getY() < -8.0:
                    # recycle ahead
                    obs.setY(max_y + random.uniform(8.0, 13.0))
                    max_y = obs.getY()
                    new_lane = random.randint(0, 2)
                    obs.setX(LANES[new_lane])

            # Update score
            self.score = int(self.distance)
            self.txt.setText(f"Score: {self.score}   Speed: {self.speed:.1f}")

            # Collisions
            self.cTrav.traverse(self.render)
            if self.cQueue.getNumEntries() > 0:
                self.cQueue.sortEntries()
                # any hit is game over
                self.game_over = True
                self.txt2.setText('GAME OVER\nAppuie sur R pour recommencer')

        return Task.cont


if __name__ == '__main__':
    app = RunnerGame()
    app.run()
