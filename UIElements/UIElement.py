import pygame

class UIElement:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def contains(self, position):
        return position[0] >= self.x and position[0] <= self.x + self.width and position[1] >= self.y and position[1] <= self.y + self.height

    def draw(self, surface: pygame.Surface):
        pass