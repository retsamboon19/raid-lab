"""Seeded System.Random used by original153 SpotRandom.Shared.

GameAssembly: ctor 0x40e3d30, InternalSample 0x40e3810,
RandomSelect.GetRandom 0x717d320. This reproduces the generator, not the
whole engine's call order (which also includes animation and weapon draws).
"""
import random


class OriginalRandom(random.Random):
    def seed(self, a=0, version=2):
        seed = int(a)
        subtraction = 2147483647 if seed == -2147483648 else abs(seed)
        mj = 161803398 - subtraction
        self._array = [0] * 56
        self._array[55] = mj
        mk = 1
        for i in range(1, 55):
            ii = (21 * i) % 55
            self._array[ii] = mk
            mk = mj - mk
            if mk < 0:
                mk += 2147483647
            mj = self._array[ii]
        for _ in range(4):
            for i in range(1, 56):
                self._array[i] -= self._array[1 + (i + 30) % 55]
                if self._array[i] < 0:
                    self._array[i] += 2147483647
        self._inext, self._inextp = 0, 21
        self.gauss_next = None

    def next_int(self):
        i, j = self._inext + 1, self._inextp + 1
        if i >= 56:
            i = 1
        if j >= 56:
            j = 1
        value = self._array[i] - self._array[j]
        if value == 2147483647:
            value -= 1
        if value < 0:
            value += 2147483647
        self._array[i] = value
        self._inext, self._inextp = i, j
        return value

    def random(self):
        return self.next_int() * (1.0 / 2147483647)

    def _randbelow(self, n):
        # SpotRandom.RandomSelect invokes System.Random.Next(0, count).
        return int(self.random() * n)
