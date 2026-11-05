import pygame

class Label:
    def __init__(self, font: pygame.font.Font, text: str = "", color = (0, 0, 0), antialias: bool = False) -> None:
        self.font = font
        self.text = self.font.render(text, 
                                     antialias,
                                     color)

        self.rect = self.text.get_rect()

        self.string = text
        self.color = color
        self.antialias = antialias


    def set_position(self, x, y):
        self.rect.left = x
        self.rect.top  = y
    
    def set_center(self, x, y):
        self.rect.center = (x, y)

    
    def set_color(self, color):
        self.color = color
        self.text = self.font.render(self.string, 
                                     color,
                                     self.antialias)

    def set_text(self, text: str):
        self.string = text
        self.text = self.font.render(text, 
                                     self.color,
                                     self.antialias)
    
    def draw(self, surface: pygame.Surface):
        surface.blit(self.text, self.rect)
