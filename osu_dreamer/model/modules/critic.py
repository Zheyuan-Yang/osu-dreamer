
from dataclasses import dataclass

from jaxtyping import Float

import numpy as np

import torch as th
from torch import nn, Tensor
import torch.nn.functional as F

from osu_dreamer.common.residual import ResStack

from osu_dreamer.data.beatmap.encode import CursorSignals


CRITIC_FEATURES = 4
def cursor_features(x: Float[Tensor, "B X L"]) -> Float[Tensor, str(f"B {CRITIC_FEATURES} L")]:
    cursor = x[:,CursorSignals]
    cursor_diff = F.pad(cursor[...,1:] - cursor[...,:-1], (1,0), mode='replicate')
    return th.cat([ cursor, cursor_diff ], dim=1)

@dataclass
class CriticArgs:
    h_dim: int
    stack_depth: int
    wave_depth: int

class Critic(nn.Module):
    def __init__(
        self,
        x_dim: int,
        args: CriticArgs,
    ):
        super().__init__()

        self.net = nn.Sequential(
            nn.Conv1d(CRITIC_FEATURES, args.h_dim, 1),
            ResStack(args.h_dim, [
                nn.Sequential(
                    nn.ZeroPad1d((2**d,0)),
                    nn.Conv1d(args.h_dim, 2*args.h_dim, 2, dilation=2**d),
                    nn.GLU(dim=1),
                )
                for d in np.arange(args.stack_depth) % args.wave_depth
            ]), # wave net
            nn.Conv1d(args.h_dim, x_dim, 1),
        )

        for m in self.modules():
            if isinstance(m, th.nn.modules.conv._ConvNd):
                th.nn.utils.spectral_norm(m)

    def forward(
        self, 
        cursor: Float[Tensor, "B X L"],
    ) -> Float[Tensor, "B X L"]:
        return self.net(cursor_features(cursor))