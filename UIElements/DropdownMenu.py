from UIElements.UIElement import UIElement
import pygame

class DropdownMenu(UIElement):
    def __init__(self, x: int, y: int, width: int, height: int, options: list[str], font: pygame.font.Font, onValueChanged = None, start_value = 0) -> None:
        super(DropdownMenu, self).__init__(x, y, width, height)

        self.options = [ font.render(option, False, (0, 0, 0)) for option in options ]
        self.option_strings = options.copy()
        self.onValueChanged = onValueChanged

        self.isOpen = False

        self.chosen = start_value


    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, (180, 180, 180), (
            self.x, self.y, self.width, self.height
        ))

        surface.blit( self.options[self.chosen], (self.x + 15, self.y + 15) )

        if self.isOpen:
            for y, option in enumerate(self.options):
                draw_y = self.y + (y + 1) * self.height
                pygame.draw.rect(surface, (180, 180, 180), (
                    self.x, draw_y, self.width, self.height
                ))
                surface.blit( option, (self.x + 15, draw_y + 15) )


    def contains(self, position):
        check_height = (len(self.options) + 1) * self.height if self.isOpen else self.height

        return position[0] >= self.x and position[0] <= self.x + self.width and position[1] >= self.y and position[1] <= self.y + check_height  


    def on_click(self, position):
        if not self.contains(position):
            self.isOpen = False
            return False

        if not self.isOpen:
            self.isOpen = True
            return True

        height = position[1] - self.y
        option = height // self.height

        self.isOpen = False

        if option == 0:
            return

        self.set_value(option - 1)

        return True

    def set_value(self, value):
        self.chosen = value
        if self.onValueChanged is not None:
            self.onValueChanged( self.chosen )

