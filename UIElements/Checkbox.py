from UIElements.UIElement import UIElement
import pygame

class Checkbox(UIElement):
    def __init__(self, x: int, y: int, width: int, height: int, start_value = False) -> None:
        super(Checkbox, self).__init__(x, y, width, height)

        