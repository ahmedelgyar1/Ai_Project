import asyncio
import platform
import pygame
import sys
import random
import time
from collections import deque

pygame.init()

# Game constants
WIDTH, HEIGHT = 800, 700
ROWS, COLS = 10, 10
CELL_SIZE = 60
GRID_TOP_MARGIN = 80
GRID_WIDTH = COLS * CELL_SIZE
GRID_HEIGHT = ROWS * CELL_SIZE

# Create screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("🐭 Mouse and Cats 🐱")
clock = pygame.time.Clock()
FPS = 30

# Colors
BG_COLOR = (30, 30, 60)
GRID_COLOR = (80, 80, 120)
CELL_BG_COLOR = (40, 40, 70)
HIGHLIGHT_COLOR = (100, 200, 255, 128)
PATH_COLOR = (120, 255, 120, 180)
VISITED_COLOR = (180, 180, 255, 100)

# Fonts
try:
    FONT = pygame.font.SysFont("Segoe UI Emoji", CELL_SIZE - 15)
    TITLE_FONT = pygame.font.SysFont("Arial", 40, bold=True)
    INFO_FONT = pygame.font.SysFont("Arial", 24)
    BUTTON_FONT = pygame.font.SysFont("Arial", 28, bold=True)
    STATS_FONT = pygame.font.SysFont("Arial", 20)
except:
    FONT = pygame.font.SysFont(None, CELL_SIZE - 15)
    TITLE_FONT = pygame.font.SysFont(None, 40, bold=True)
    INFO_FONT = pygame.font.SysFont(None, 24)
    BUTTON_FONT = pygame.font.SysFont(None, 28, bold=True)
    STATS_FONT = pygame.font.SysFont(None, 20)

# Game entities
MOUSE_EMOJI = '🐭'
CAT_EMOJI = '🐱'
DOOR_EMOJI = '🚪'
WALL_EMOJI = '🧱'

# Animation settings
ANIMATION_SPEED = 8

def grid_to_screen(pos):
    return (pos[1] * CELL_SIZE, pos[0] * CELL_SIZE + GRID_TOP_MARGIN)

def draw_grid():
    grid_rect = pygame.Rect(0, GRID_TOP_MARGIN, GRID_WIDTH, GRID_HEIGHT)
    pygame.draw.rect(screen, CELL_BG_COLOR, grid_rect)
    for r in range(ROWS + 1):
        pygame.draw.line(screen, GRID_COLOR, 
                        (0, r * CELL_SIZE + GRID_TOP_MARGIN), 
                        (GRID_WIDTH, r * CELL_SIZE + GRID_TOP_MARGIN), 2)
    for c in range(COLS + 1):
        pygame.draw.line(screen, GRID_COLOR, 
                        (c * CELL_SIZE, GRID_TOP_MARGIN), 
                        (c * CELL_SIZE, GRID_HEIGHT + GRID_TOP_MARGIN), 2)

def draw_emoji(pos, emoji):
    x, y = grid_to_screen(pos)
    text = FONT.render(emoji, True, (255, 255, 255))
    text_rect = text.get_rect(center=(x + CELL_SIZE // 2, y + CELL_SIZE // 2))
    screen.blit(text, text_rect)

def highlight_cell(pos, color):
    x, y = grid_to_screen(pos)
    rect = pygame.Rect(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2)
    s = pygame.Surface((CELL_SIZE - 2, CELL_SIZE - 2), pygame.SRCALPHA)
    s.fill(color)
    screen.blit(s, (x + 1, y + 1))

def draw_entities(mouse_pos, cats, doors, walls=[], visited=[], path=[]):
    for pos in visited:
        highlight_cell(pos, VISITED_COLOR)
    for pos in path:
        highlight_cell(pos, PATH_COLOR)
    for door in doors:
        draw_emoji(door, DOOR_EMOJI)
    for wall in walls:
        draw_emoji(wall, WALL_EMOJI)
    draw_emoji(mouse_pos, MOUSE_EMOJI)
    for cat in cats:
        draw_emoji(cat, CAT_EMOJI)

def move_cat_towards(cat, target, walls=[]):
    original_pos = cat.copy()
    dr = target[0] - cat[0]
    dc = target[1] - cat[1]
    new_pos = cat.copy()
    if abs(dr) > abs(dc):
        new_pos[0] += 1 if dr > 0 else -1 if dr < 0 else 0
    else:
        new_pos[1] += 1 if dc > 0 else -1 if dc < 0 else 0
    if (0 <= new_pos[0] < ROWS and 0 <= new_pos[1] < COLS and 
            new_pos not in walls):
        cat[0], cat[1] = new_pos[0], new_pos[1]
        return True
    new_pos = cat.copy()
    if abs(dr) <= abs(dc):
        new_pos[0] += 1 if dr > 0 else -1 if dr < 0 else 0
    else:
        new_pos[1] += 1 if dc > 0 else -1 if dc < 0 else 0
    if (0 <= new_pos[0] < ROWS and 0 <= new_pos[1] < COLS and 
            new_pos not in walls):
        cat[0], cat[1] = new_pos[0], new_pos[1]
        return True
    return False

def show_message(text, color=(255, 255, 255), duration=2000):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    screen.blit(overlay, (0, 0))
    msg = TITLE_FONT.render(text, True, color)
    padding = 20
    box_rect = pygame.Rect(0, 0, msg.get_width() + padding*2, msg.get_height() + padding*2)
    box_rect.center = (WIDTH // 2, HEIGHT // 2)
    pygame.draw.rect(screen, (50, 50, 80), box_rect, border_radius=10)
    pygame.draw.rect(screen, (100, 100, 150), box_rect, 3, border_radius=10)
    text_rect = msg.get_rect(center=box_rect.center)
    screen.blit(msg, text_rect)
    pygame.display.flip()
    if platform.system() == "Emscripten":
        # Non-blocking delay for Pyodide
        async def async_wait():
            await asyncio.sleep(duration / 1000)
        asyncio.ensure_future(async_wait())
    else:
        pygame.time.wait(duration)

def get_random_pos(exclude=[]):
    attempts = 0
    while attempts < 100:
        pos = [random.randint(0, ROWS - 1), random.randint(0, COLS - 1)]
        if pos not in exclude:
            return pos
        attempts += 1
    for r in range(ROWS):
        for c in range(COLS):
            pos = [r, c]
            if pos not in exclude:
                return pos
    return [0, 0]

def bfs_solver(start, cats, doors, walls=[], animate=False, delay=0.1):
    queue = deque([(start, [])])
    visited = set([tuple(start)])
    all_visited = [start]
    found_path = None
    sim_cats = [cat.copy() for cat in cats]
    nodes_explored = 0
    max_queue_size = 1
    while queue and not found_path:
        nodes_explored += 1
        current_pos, path = queue.popleft()
        if current_pos in doors:
            found_path = path
            break
        for direction in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_pos = [current_pos[0] + direction[0], current_pos[1] + direction[1]]
            if (0 <= new_pos[0] < ROWS and 0 <= new_pos[1] < COLS and 
                    tuple(new_pos) not in visited and 
                    new_pos not in walls):
                cat_would_catch = False
                for cat in sim_cats:
                    if new_pos == cat:
                        cat_would_catch = True
                        break
                if not cat_would_catch:
                    visited.add(tuple(new_pos))
                    all_visited.append(new_pos)
                    queue.append((new_pos, path + [new_pos]))
                    max_queue_size = max(max_queue_size, len(queue))
                    if animate:
                        screen.fill(BG_COLOR)
                        draw_grid()
                        draw_entities(start, cats, doors, walls, all_visited, path + [new_pos])
                        stats_text = f"Nodes explored: {nodes_explored} | Queue size: {len(queue)} | Max queue: {max_queue_size}"
                        stats = INFO_FONT.render(stats_text, True, (200, 200, 255))
                        screen.blit(stats, (10, HEIGHT - 40))
                        pygame.display.flip()
                        if platform.system() == "Emscripten":
                            async def async_delay():
                                await asyncio.sleep(delay)
                            asyncio.ensure_future(async_delay())
                        else:
                            time.sleep(delay)
    stats = {
        "nodes_explored": nodes_explored,
        "max_queue_size": max_queue_size,
        "path_length": len(found_path) if found_path else 0,
        "success": found_path is not None
    }
    return found_path, all_visited, stats

def draw_button(text, rect, active=False, hover=False):
    if active:
        color = (100, 200, 255)
    elif hover:
        color = (80, 160, 220)
    else:
        color = (60, 100, 180)
    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, (200, 200, 255), rect, 2, border_radius=10)
    label = BUTTON_FONT.render(text, True, (255, 255, 255))
    label_rect = label.get_rect(center=rect.center)
    screen.blit(label, label_rect)
    return rect

def draw_slider(text, rect, min_val, max_val, current_val, active=False):
    label = INFO_FONT.render(f"{text}: {current_val}", True, (200, 200, 255))
    label_rect = label.get_rect(topleft=(rect.x, rect.y - 30))
    screen.blit(label, label_rect)
    track_rect = pygame.Rect(rect.x, rect.y + rect.height // 2 - 2, rect.width, 4)
    pygame.draw.rect(screen, (100, 100, 150), track_rect, border_radius=2)
    handle_pos = rect.x + int((current_val - min_val) / (max_val - min_val) * rect.width)
    handle_rect = pygame.Rect(handle_pos - 8, rect.y, 16, rect.height)
    color = (100, 200, 255) if active else (80, 160, 220)
    pygame.draw.rect(screen, color, handle_rect, border_radius=8)
    pygame.draw.rect(screen, (200, 200, 255), handle_rect, 2, border_radius=8)
    return handle_rect

def handle_slider_drag(rect, min_val, max_val, current_val, mouse_pos):
    if rect.collidepoint(mouse_pos):
        ratio = (mouse_pos[0] - rect.x) / rect.width
        new_val = min(max_val, max(min_val, int(min_val + ratio * (max_val - min_val))))
        return new_val, True
    return current_val, False

def draw_title_screen():
    screen.fill(BG_COLOR)
    title = TITLE_FONT.render("🐭 Mouse and Cats 🐱", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    subtitle = INFO_FONT.render("Help the mouse escape from the cats!", True, (200, 200, 255))
    screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 100))
    play_button = pygame.Rect(WIDTH//2 - 200, HEIGHT//2 - 60, 180, 50)
    bfs_button = pygame.Rect(WIDTH//2 + 20, HEIGHT//2 - 60, 180, 50)
    quit_button = pygame.Rect(WIDTH//2 - 90, HEIGHT//2 + 20, 180, 50)
    mouse_pos = pygame.mouse.get_pos()
    play_hover = play_button.collidepoint(mouse_pos)
    bfs_hover = bfs_button.collidepoint(mouse_pos)
    quit_hover = quit_button.collidepoint(mouse_pos)
    draw_button("Play Game", play_button, hover=play_hover)
    draw_button("BFS Solver", bfs_button, hover=bfs_hover)
    draw_button("Quit", quit_button, hover=quit_hover)
    pygame.display.flip()
    return play_button, bfs_button, quit_button

def draw_setup_screen(num_cats, num_doors, num_walls):
    screen.fill(BG_COLOR)
    title = TITLE_FONT.render("Game Setup", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    cats_slider_rect = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 - 120, 300, 30)
    doors_slider_rect = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 - 40, 300, 30)
    walls_slider_rect = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 + 40, 300, 30)
    cats_handle = draw_slider("Number of Cats", cats_slider_rect, 1, 10, num_cats)
    doors_handle = draw_slider("Number of Doors", doors_slider_rect, 1, 5, num_doors)
    walls_handle = draw_slider("Number of Walls", walls_slider_rect, 0, 20, num_walls)
    start_button = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 120, 200, 50)
    mouse_pos = pygame.mouse.get_pos()
    start_hover = start_button.collidepoint(mouse_pos)
    draw_button("Start Game", start_button, hover=start_hover)
    pygame.display.flip()
    return cats_slider_rect, doors_slider_rect, walls_slider_rect, start_button

def rate_bfs_performance(stats, num_cats, num_doors):
    path_score = 10
    if stats["path_length"] > 0:
        path_score = max(0, 10 - (stats["path_length"] // 5))
    else:
        path_score = 0
    max_nodes = ROWS * COLS
    search_score = 10 - min(10, (stats["nodes_explored"] / max_nodes) * 10)
    difficulty = (num_cats / num_doors) * 2
    difficulty_bonus = min(5, difficulty)
    final_score = (path_score * 0.5) + (search_score * 0.3) + (difficulty_bonus * 0.2)
    final_score = round(min(10, max(0, final_score)), 1)
    if final_score >= 9:
        rating_text = "Excellent!"
    elif final_score >= 7:
        rating_text = "Very Good"
    elif final_score >= 5:
        rating_text = "Good"
    elif final_score >= 3:
        rating_text = "Fair"
    else:
        rating_text = "Poor"
    return final_score, rating_text

def draw_bfs_results(stats, num_cats, num_doors, bfs_score, rating_text):
    screen.fill(BG_COLOR)
    title = TITLE_FONT.render("BFS Solver Results", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    y_pos = 120
    stats_items = [
        f"Path length: {stats['path_length']} steps",
        f"Nodes explored: {stats['nodes_explored']}",
        f"Max queue size: {stats['max_queue_size']}",
        f"Success: {'Yes' if stats['success'] else 'No'}"
    ]
    for item in stats_items:
        text = INFO_FONT.render(item, True, (200, 200, 255))
        screen.blit(text, (WIDTH//2 - text.get_width()//2, y_pos))
        y_pos += 40
    env_text = INFO_FONT.render(f"Environment: {num_cats} cats, {num_doors} doors", True, (200, 200, 255))
    screen.blit(env_text, (WIDTH//2 - env_text.get_width()//2, y_pos))
    y_pos += 60
    score_text = TITLE_FONT.render(f"BFS Rating: {bfs_score}/10", True, (255, 220, 100))
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, y_pos))
    y_pos += 40
    rating = TITLE_FONT.render(rating_text, True, (255, 220, 100))
    screen.blit(rating, (WIDTH//2 - rating.get_width()//2, y_pos))
    y_pos += 80
    back_button = pygame.Rect(WIDTH//2 - 100, y_pos, 200, 50)
    mouse_pos = pygame.mouse.get_pos()
    back_hover = back_button.collidepoint(mouse_pos)
    draw_button("Back to Menu", back_button, hover=back_hover)
    pygame.display.flip()
    return back_button

def draw_game_info(mouse_pos, cats, doors, walls):
    info_rect = pygame.Rect(0, 0, WIDTH, GRID_TOP_MARGIN)
    pygame.draw.rect(screen, (25, 25, 50), info_rect)
    pygame.draw.line(screen, GRID_COLOR, (0, GRID_TOP_MARGIN), (WIDTH, GRID_TOP_MARGIN), 2)
    title = TITLE_FONT.render("🐭 Mouse and Cats 🐱", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 10))
    stats = INFO_FONT.render(f"Cats: {len(cats)} | Doors: {len(doors)} | Walls: {len(walls)}", True, (200, 200, 255))
    screen.blit(stats, (10, 50))
    controls = INFO_FONT.render("Use arrow keys to move | ESC to quit", True, (200, 200, 255))
    screen.blit(controls, (WIDTH - controls.get_width() - 10, 50))

async def main():
    while True:
        play_button, bfs_button, quit_button = draw_title_screen()
        choice = None
        while choice is None:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    if play_button.collidepoint(mouse_pos):
                        choice = "play"
                    elif bfs_button.collidepoint(mouse_pos):
                        choice = "bfs"
                    elif quit_button.collidepoint(mouse_pos):
                        return
            play_button, bfs_button, quit_button = draw_title_screen()
            pygame.display.flip()
   # Ensure the screen is updated
            await asyncio.sleep(1.0 / FPS)
        
        num_cats = 3
        num_doors = 2
        num_walls = 5
        dragging_slider = None
        setup_done = False
        while not setup_done:
            cats_slider, doors_slider, walls_slider, start_button = draw_setup_screen(
                num_cats, num_doors, num_walls
            )
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    if cats_slider.collidepoint(mouse_pos):
                        dragging_slider = "cats"
                    elif doors_slider.collidepoint(mouse_pos):
                        dragging_slider = "doors"
                    elif walls_slider.collidepoint(mouse_pos):
                        dragging_slider = "walls"
                    elif start_button.collidepoint(mouse_pos):
                        setup_done = True
                if event.type == pygame.MOUSEBUTTONUP:
                    dragging_slider = None
                if event.type == pygame.MOUSEMOTION and dragging_slider:
                    mouse_pos = pygame.mouse.get_pos()
                    if dragging_slider == "cats":
                        num_cats, _ = handle_slider_drag(cats_slider, 1, 10, num_cats, mouse_pos)
                    elif dragging_slider == "doors":
                        num_doors, _ = handle_slider_drag(doors_slider, 1, 5, num_doors, mouse_pos)
                    elif dragging_slider == "walls":
                        num_walls, _ = handle_slider_drag(walls_slider, 0, 20, num_walls, mouse_pos)
            await asyncio.sleep(1.0 / FPS)
        
        mouse_pos = get_random_pos()
        doors = []
        cats = []
        walls = []
        used_positions = [mouse_pos]
        for _ in range(num_doors):
            door_pos = get_random_pos(exclude=used_positions)
            doors.append(door_pos)
            used_positions.append(door_pos)
        for _ in range(num_cats):
            cat_pos = get_random_pos(exclude=used_positions)
            cats.append(cat_pos)
            used_positions.append(cat_pos)
        for _ in range(num_walls):
            wall_pos = get_random_pos(exclude=used_positions)
            walls.append(wall_pos)
            used_positions.append(wall_pos)
        
        if choice == "play":
            running = True
            game_over = False
            while running:
                screen.fill(BG_COLOR)
                draw_grid()
                draw_entities(mouse_pos, cats, doors, walls)
                draw_game_info(mouse_pos, cats, doors, walls)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                if not game_over:
                    moved = False
                    keys = pygame.key.get_pressed()
                    new_pos = mouse_pos.copy()
                    if keys[pygame.K_UP] and mouse_pos[0] > 0:
                        new_pos[0] -= 1
                        moved = True
                    elif keys[pygame.K_DOWN] and mouse_pos[0] < ROWS - 1:
                        new_pos[0] += 1
                        moved = True
                    elif keys[pygame.K_LEFT] and mouse_pos[1] > 0:
                        new_pos[1] -= 1
                        moved = True
                    elif keys[pygame.K_RIGHT] and mouse_pos[1] < COLS - 1:
                        new_pos[1] += 1
                        moved = True
                    if moved and new_pos not in walls:
                        mouse_pos = new_pos
                        for cat in cats:
                            move_cat_towards(cat, mouse_pos, walls)
                    if mouse_pos in doors:
                        show_message("🎉 You won! Mouse reached a door!", (100, 255, 100))
                        game_over = True
                        running = False
                    if any(mouse_pos == cat for cat in cats):
                        show_message("💀 You lost! A cat caught you!", (255, 100, 100))
                        game_over = True
                        running = False
                pygame.display.flip()
                await asyncio.sleep(1.0 / 10)  # 10 FPS for manual play
        elif choice == "bfs":
            screen.fill(BG_COLOR)
            draw_grid()
            draw_entities(mouse_pos, cats, doors, walls)
            pygame.display.flip()
            show_message("Running BFS solver...", (100, 200, 255), 1000)
            path, visited, stats = bfs_solver(mouse_pos, cats, doors, walls, animate=True, delay=0.05)
            if path:
                show_message("✅ BFS found a path!", (100, 255, 100), 1000)
                mouse_clone = mouse_pos.copy()
                cats_clone = [cat.copy() for cat in cats]
                for step in path:
                    mouse_clone = step
                    for cat in cats_clone:
                        move_cat_towards(cat, mouse_clone, walls)
                    screen.fill(BG_COLOR)
                    draw_grid()
                    draw_entities(mouse_clone, cats_clone, doors, walls, visited, path)
                    draw_game_info(mouse_clone, cats_clone, doors, walls)
                    pygame.display.flip()
                    if platform.system() == "Emscripten":
                        await asyncio.sleep(0.3)
                    else:
                        pygame.time.wait(300)
                    if any(mouse_clone == cat for cat in cats_clone):
                        show_message("💀 BFS path failed! A cat caught the mouse!", (255, 100, 100))
                        break
                bfs_score, rating_text = rate_bfs_performance(stats, num_cats, num_doors)
                back_button = draw_bfs_results(stats, num_cats, num_doors, bfs_score, rating_text)
                waiting_for_click = True
                while waiting_for_click:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            if back_button.collidepoint(event.pos):
                                waiting_for_click = False
                                break
                    back_button = draw_bfs_results(stats, num_cats, num_doors, bfs_score, rating_text)
                    await asyncio.sleep(1.0 / FPS)
            else:
                show_message("❌ No path found! Mouse is trapped!", (255, 100, 100))
                stats["success"] = False
                bfs_score, rating_text = rate_bfs_performance(stats, num_cats, num_doors)
                back_button = draw_bfs_results(stats, num_cats, num_doors, bfs_score, rating_text)
                waiting_for_click = True
                while waiting_for_click:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            if back_button.collidepoint(event.pos):
                                waiting_for_click = False
                                break
                    back_button = draw_bfs_results(stats, num_cats, num_doors, bfs_score, rating_text)
                    await asyncio.sleep(1.0 / FPS)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())