import asyncio
from datetime import datetime
from typing import Optional, Union

import discord
import wavelink
from discord.ext import commands

from .errors import (
    AlreadyConnectedToChannel,
    NoTracksFound,
    NoVoiceChannel,
    QueueIsEmpty,
)
from .queue import Queue
from .types import OPTIONS


class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = Queue()
        self.eq_levels = [0.0] * 15

    async def connect(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None
    ):
        if self.is_connected:
            raise AlreadyConnectedToChannel()

        if (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            raise NoVoiceChannel()

        await super().connect(channel.id)
        return channel

    async def teardown(self):
        try:
            await self.destroy()
        except KeyError:
            pass

    async def add_tracks(
        self,
        ctx: commands.Context,
        tracks: Union[wavelink.Track, wavelink.TrackPlaylist],
    ):
        if not tracks:
            raise NoTracksFound()

        if isinstance(tracks, wavelink.TrackPlaylist):
            self.queue.add(*tracks.tracks)
        elif len(tracks) == 1:
            self.queue.add(tracks[0])
            await ctx.send(f"Added {tracks[0].title} to the queue.")
        else:
            if (track := await self.choose_track(ctx, tracks)) is not None:
                self.queue.add(track)
                await ctx.send(f"Added {track.title} to the queue.")

        if not self.is_playing and not self.queue.is_empty:
            await self.start_playback()

    async def choose_track(self, ctx: commands.Context, tracks: wavelink.TrackPlaylist):
        def _check(r, u):
            return (
                r.emoji in OPTIONS.keys() and u == ctx.author and r.message.id == msg.id
            )

        embed = discord.Embed(
            title="Choose a song",
            description=(
                "\n".join(
                    f"**{i+1}.** {t.title} ({t.length//60000}:{str(t.length%60).zfill(2)})"
                    for i, t in enumerate(tracks[:5])
                )
            ),
            colour=ctx.author.colour,
            timestamp=datetime.utcnow(),
        )
        embed.set_author(name="Query Results")
        embed.set_footer(
            text=f"Invoked by {ctx.author.display_name}", icon_url=ctx.author.avatar_url
        )

        msg = await ctx.send(embed=embed)
        tasks = [
            msg.add_reaction(emoji)
            for emoji in list(OPTIONS.keys())[: min(len(tracks), len(OPTIONS))]
        ]
        asyncio.gather(*tasks)

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", timeout=60.0, check=_check
            )
        except asyncio.TimeoutError:
            await msg.delete()
            await ctx.message.delete()
        else:
            await msg.delete()
            return tracks[OPTIONS[reaction.emoji]]

    async def start_playback(self):
        await self.play(self.queue.current_track)

    async def advance(self):
        try:
            if (track := self.queue.get_next_track()) is not None:
                await self.play(track)
        except QueueIsEmpty:
            pass

    async def repeat_track(self):
        await self.play(self.queue.current_track)
