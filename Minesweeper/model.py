import random
from typing import Any

import torch
from torch import nn


class ResidualBlock(nn.Module):
    def __init__(self, in_channels: int, inner_channels: int, out_channels : int | None = None, group_size = 8, device = "cpu") -> None:
        super().__init__()

        if out_channels is None:
            out_channels = in_channels

        self.sequence = nn.Sequential(
            nn.Conv2d(
                in_channels  = in_channels,
                out_channels = inner_channels,
                kernel_size  = 3,
                padding      = 1,
                device=device
            ),
            nn.GroupNorm(group_size, inner_channels, device=device),
            nn.ReLU(),

            nn.Conv2d(
                in_channels  = inner_channels,
                out_channels = out_channels,
                kernel_size  = 3,
                padding      = 1,
                device=device
            ),
            nn.GroupNorm(group_size, out_channels, device=device)
        )

        if in_channels != out_channels:
            self.skip = nn.Conv2d(in_channels, out_channels, 1, device=device)
        else:
            self.skip = nn.Identity(device=device)

        self.relu = nn.ReLU()

    def forward(self, x: torch.Tensor):
        return self.relu( self.sequence(x) + self.skip(x) )


class SpatialSelfAttention(nn.Module):
    def __init__(self, channels, num_heads, device = "cpu") -> None:
        super().__init__()

        assert channels % num_heads == 0

        self.norm = nn.LayerNorm(channels, device=device)

        self.attention = nn.MultiheadAttention(
            embed_dim=channels,
            num_heads=num_heads,
            batch_first=True,
            device=device,
        )

    def forward(self, x):
        # x: (B, C, H, W)
        B, C, H, W = x.shape

        # Convert each spatial position into a token:
        # (B, C, H, W) -> (B, H*W, C)
        tokens = x.flatten(2).transpose(1, 2)

        # Pre-normalization
        normalized = self.norm(tokens)

        # Global self-attention
        attended, _ = self.attention(
            normalized,
            normalized,
            normalized,
            need_weights=False,
        )

        # Residual connection
        tokens = tokens + attended

        # Restore the original shape: (B, C, H, W)
        return tokens.transpose(1, 2).reshape(B, C, H, W)


class MinesweeperModel(nn.Module):
    def __init__(self, input_channels: int, device="cpu") -> None:
        super(MinesweeperModel, self).__init__()


        self.in_conv = nn.Sequential(
            nn.Conv2d(
                in_channels     = input_channels,
                out_channels    = 32,
                kernel_size     = 3,
                padding         = 1,
                device=device
            ),
            nn.GroupNorm(8, 32, device=device),

            # SpatialSelfAttention(32, 4, device),

            nn.ReLU(),

            ResidualBlock(32, 32, device=device),

            # ResidualBlock(32, 32, device=device),
        )

        self.action_head = nn.Sequential( #click, flag, unflag
            nn.Conv2d(32, 3, 1, device=device) 
        )
        
        self.value_head = nn.Sequential(
            nn.Conv2d(32, 64, 3, padding=1, device=device),
            nn.GroupNorm(8, 64, device=device),
            nn.ReLU(),

            ResidualBlock(64, 64, device=device),
            
            nn.Conv2d(64, 1, 1, device=device),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
        )


    def forward(self, x: torch.Tensor):
        if len(x.shape) == 3:
            x = x.unsqueeze(0)

        out = self.in_conv(x)


        return self.action_head(out), self.value_head(out)#, self.field_head(out)




def get_action_distribution( logits: torch.Tensor, mask: torch.Tensor | None):
    
    logits = logits.clone()

    if mask is not None:
        logits += mask

    try:
        return torch.distributions.Categorical( logits = logits.flatten(1) )
    except Exception as e:
        print(mask)

        raise e


def get_action_index( 
        move: torch.Tensor, 
        mask: torch.Tensor | None,
        random_move: bool | float = False):

    
    dist = get_action_distribution(move, mask)

    if random_move == True:
        return int( dist.sample().item()) 
    
    elif random_move == False:
        return int( torch.argmax( dist.probs ).item() )

    if random.random() < random_move:
        return int( dist.sample().item()) 

    return int( torch.argmax( dist.probs ).item() )



def get_action(
        action_index,
        board_x: int, 
        board_y: int):
    ACION_MAX = board_x * board_y

    action = 0

    action = action_index // ACION_MAX
    index = action_index % ACION_MAX

    return index, action




if __name__ == "__main__":
    model = MinesweeperModel(5)

    print(model)
