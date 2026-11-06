from UIElements.UIElement import UIElement
from UIElements.Label import Label
import pygame

class Checkbox(UIElement):
    def __init__(self, x: int, y: int, width: int, height: int, start_value = False, on_value_changed = None) -> None:
        self.checked = start_value

        self.on_value_changed = on_value_changed

        super(Checkbox, self).__init__(x, y, width, height)

    def draw(self, surface):
        pygame.draw.rect(surface, (0, 0, 0), (self.x, self.y, self.width, self.height))

        if not self.checked:
           pygame.draw.rect(surface, (255, 255, 255), (self.x + 10, self.y + 10, self.width - 20, self.height - 20))


    def on_click(self, position):
        if not self.contains(position):
            return False

        self.checked = not self.checked

        if self.on_value_changed != None:
            self.on_value_changed(self.checked)
        
        return True
        