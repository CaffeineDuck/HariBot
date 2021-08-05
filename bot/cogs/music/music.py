import datetime as dt
from typing import Any, Optional, Union

import discord
import wavelink
from discord.ext import commands

from ...core import Bot
from ...utils.bettercog import BetterCog
from .utils import (
    HZ_BANDS,
    LYRICS_URL,
    TIME_REGEX,
    URL_REGEX,
    EQGainOutOfBounds,
    InvalidEQPreset,
    InvalidRepeatMode,
    InvalidTimeString,
    MaxVolume,
    MinVolume,
    NoLyricsFound,
    NoMoreTracks,
    NonExistentEQBand,
    NoPreviousTracks,
    Player,
    PlayerIsAlreadyPaused,
    QueueIsEmpty,
    RepeatMode,
    VolumeTooHigh,
    VolumeTooLow,
)


class Music(BetterCog, wavelink.WavelinkMixin):
    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.wavelink = bot.wavelink_client

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.bot and after.channel is None:
            if not [m for m in before.channel.members if not m.bot]:
                await self.get_player(member.guild).teardown()

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node):
        print(f" Wavelink node `{node.identifier}` ready.")

    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, _: wavelink.Node, payload: Any):
        if payload.player.queue.repeat_mode == RepeatMode.ONE:
            await payload.player.repeat_track()
        else:
            await payload.player.advance()

    async def cog_check(self, ctx: commands.Context):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("Music commands are not available in DMs.")
            return False

        return True

    def get_player(self, obj: Union[discord.Guild, commands.Context]):
        if isinstance(obj, commands.Context):
            return self.wavelink.get_player(obj.guild.id, cls=Player, context=obj)
        elif isinstance(obj, discord.Guild):
            return self.wavelink.get_player(obj.id, cls=Player)

    @commands.command(name="connect", aliases=["join"])
    async def connect_command(
        self, ctx: commands.Context, *, channel: Optional[discord.VoiceChannel]
    ):
        player = self.get_player(ctx)
        channel = await player.connect(ctx, channel)
        await ctx.send(f"Connected to {channel.name}.")

    @commands.command(name="disconnect", aliases=["leave", "fuckoff"])
    async def disconnect_command(self, ctx: commands.Context):
        player = self.get_player(ctx)
        await player.teardown()
        await ctx.send("Disconnected.")

    @commands.command(name="play", aliases=["p"])
    async def play_command(self, ctx: commands.Context, *, query: Optional[str]):
        player: Player = self.get_player(ctx)

        if not player.is_connected:
            await player.connect(ctx)

        if query is None:
            if player.queue.is_empty:
                raise QueueIsEmpty()

            await player.set_pause(False)
            await ctx.send("Playback resumed.")

        else:
            query = query.strip("<>")
            if not URL_REGEX.match(query):
                query = f"ytsearch:{query}"

            await player.add_tracks(ctx, await self.wavelink.get_tracks(query))

    @commands.command(name="pause")
    async def pause_command(self, ctx: commands.Context):
        player = self.get_player(ctx)

        if player.is_paused:
            raise PlayerIsAlreadyPaused()

        await player.set_pause(True)
        await ctx.send("Playback paused.")

    @commands.command(name="stop")
    async def stop_command(self, ctx: commands.Context):
        player = self.get_player(ctx)
        player.queue.empty()
        await player.stop()
        await ctx.send("Playback stopped.")

    @commands.command(name="next", aliases=["skip"])
    async def next_command(self, ctx: commands.Context):
        player = self.get_player(ctx)

        if not player.queue.upcoming:
            raise NoMoreTracks()

        await player.stop()
        await ctx.send("Playing next track in queue.")

    @commands.command(name="previous")
    async def previous_command(self, ctx: commands.Context):
        player = self.get_player(ctx)

        if not player.queue.history:
            raise NoPreviousTracks()

        player.queue.position -= 2
        await player.stop()
        await ctx.send("Playing previous track in queue.")

    @commands.command(name="shuffle")
    async def shuffle_command(self, ctx: commands.Context):
        player = self.get_player(ctx)
        player.queue.shuffle()
        await ctx.send("Queue shuffled.")

    @commands.command(name="repeat")
    async def repeat_command(self, ctx: commands.Context, mode: str):
        if mode not in RepeatMode:
            raise InvalidRepeatMode()

        player = self.get_player(ctx)
        player.queue.set_repeat_mode(mode)
        await ctx.send(f"The repeat mode has been set to {mode}.")

    @commands.command(name="queue")
    async def queue_command(self, ctx: commands.Context, show: Optional[int] = 10):
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        embed = discord.Embed(
            title="Queue",
            description=f"Showing up to next {show} tracks",
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow(),
        )
        embed.set_author(name="Query Results")
        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar_url,
        )
        embed.add_field(
            name="Currently playing",
            value=getattr(
                player.queue.current_track, "title", "No tracks currently playing."
            ),
            inline=False,
        )
        if upcoming := player.queue.upcoming:
            embed.add_field(
                name="Next up",
                value="\n".join(t.title for t in upcoming[:show]),
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.group(name="volume", invoke_without_command=True)
    async def volume_group(self, ctx: commands.Context, volume: int):
        player = self.get_player(ctx)

        if volume < 0:
            raise VolumeTooLow()

        if volume > 150:
            raise VolumeTooHigh()

        await player.set_volume(volume)
        await ctx.send(f"Volume set to {volume:,}%")

    @volume_group.command(name="up")
    async def volume_up_command(self, ctx: commands.Context):
        player = self.get_player(ctx)

        if player.volume == 150:
            raise MaxVolume()

        await player.set_volume(value := min(player.volume + 10, 150))
        await ctx.send(f"Volume set to {value:,}%")

    @volume_group.command(name="down")
    async def volume_down_command(self, ctx: commands.Context):
        player = self.get_player(ctx)

        if player.volume == 0:
            raise MinVolume()

        await player.set_volume(value := max(0, player.volume - 10))
        await ctx.send(f"Volume set to {value:,}%")

    @commands.command(name="lyrics")
    async def lyrics_command(self, ctx: commands.Context, name: Optional[str]):
        player = self.get_player(ctx)
        name = name or player.queue.current_track.title

        async with ctx.typing():
            async with self.bot.session.get(LYRICS_URL + name) as r:
                if not 200 <= r.status <= 299:
                    raise NoLyricsFound()

                data = await r.json()

                if len(data["lyrics"]) > 2000:
                    return await ctx.send(f"<{data['links']['genius']}>")

                embed = discord.Embed(
                    title=data["title"],
                    description=data["lyrics"],
                    colour=ctx.author.colour,
                    timestamp=dt.datetime.utcnow(),
                )
                embed.set_thumbnail(url=data["thumbnail"]["genius"])
                embed.set_author(name=data["author"])
                await ctx.send(embed=embed)

    @commands.command(name="eq")
    async def eq_command(self, ctx, preset: str):
        player = self.get_player(ctx)

        eq = getattr(wavelink.eqs.Equalizer, preset, None)
        if not eq:
            raise InvalidEQPreset()

        await player.set_eq(eq())
        await ctx.send(f"Equaliser adjusted to the {preset} preset.")

    @commands.command(name="adveq", aliases=["aeq"])
    async def adveq_command(self, ctx, band: int, gain: float):
        player = self.get_player(ctx)

        if not 1 <= band <= 15 and band not in HZ_BANDS:
            raise NonExistentEQBand

        if band > 15:
            band = HZ_BANDS.index(band) + 1

        if abs(gain) > 10:
            raise EQGainOutOfBounds

        player.eq_levels[band - 1] = gain / 10
        eq = wavelink.eqs.Equalizer(
            levels=[(i, gain) for i, gain in enumerate(player.eq_levels)]
        )
        await player.set_eq(eq)
        await ctx.send("Equaliser adjusted.")

    @commands.command(name="playing", aliases=["np"])
    async def playing_command(self, ctx):
        player = self.get_player(ctx)

        if not player.is_playing:
            raise PlayerIsAlreadyPaused

        embed = discord.Embed(
            title="Now playing",
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow(),
        )
        embed.set_author(name="Playback Information")
        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.avatar_url,
        )
        embed.add_field(
            name="Track title", value=player.queue.current_track.title, inline=False
        )
        embed.add_field(
            name="Artist", value=player.queue.current_track.author, inline=False
        )

        position = divmod(player.position, 60000)
        length = divmod(player.queue.current_track.length, 60000)
        embed.add_field(
            name="Position",
            value=f"{int(position[0])}:{round(position[1]/1000):02}/{int(length[0])}:{round(length[1]/1000):02}",
            inline=False,
        )

        await ctx.send(embed=embed)

    @commands.command(name="skipto", aliases=["playindex"])
    async def skipto_command(self, ctx, index: int):
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty()

        if not 0 <= index <= player.queue.length:
            raise NoMoreTracks()

        player.queue.position = index - 2
        await player.stop()
        await ctx.send(f"Playing track in position {index}.")

    @commands.command(name="restart")
    async def restart_command(self, ctx):
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty()

        await player.seek(0)
        await ctx.send("Track restarted.")

    @commands.command(name="seek")
    async def seek_command(self, ctx, position: str):
        player = self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty()

        if not (match := TIME_REGEX.match(position)):
            raise InvalidTimeString()

        if match.group(3):
            secs = (int(match.group(1)) * 60) + (int(match.group(3)))
        else:
            secs = int(match.group(1))

        await player.seek(secs * 1000)
        await ctx.send("Seeked.")


def setup(bot):
    bot.add_cog(Music(bot))
