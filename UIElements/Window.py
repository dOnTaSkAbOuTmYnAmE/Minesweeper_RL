import pygame

class Window:
    def __init__(self, width: int, height: int, resizable: float = False) -> None:
        flags = 0

        self.running = False
        self.clock = pygame.time.Clock()
        
        
        if resizable:
            flags += pygame.RESIZABLE

        self.screen = pygame.display.set_mode((width, height), flags)


    def activate(self):
        self.running = True
        delta = 0.0001

        while self.running:
            for event in pygame.event.get():
                self.__handle_events__(event)


            self.__update__(delta)


            delta = self.clock.tick(60) / 1000
            delta = max(0.001, min( delta, 0.1 ))

            pygame.display.flip()
        
        pygame.quit()


    def __handle_events__(self, events: pygame.event.Event):
        pass


    def __update__(self, delta: float):
        pass