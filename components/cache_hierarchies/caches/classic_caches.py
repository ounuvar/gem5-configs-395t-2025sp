"""
Classic cache model caches for L1s, L2, LLC, and MMU cache.
Each has a wide range of consructor-customizable parameters. Empty constructors
will create caches matched roughly to an Intel Skylake.

For all cache options, see src/mem/cache/Cache.py class BaseCache
"""

from m5.objects import (
    Cache,
    Clusivity,
    BasePrefetcher,
    StridePrefetcher,
    BaseReplacementPolicy,
    LRURP,
    NULL,
)

"""
L1 data cache
"""


class L1DCache(Cache):
    def __init__(
        self,
        # FIXME TODO: Set these appropriately.
        #
        # Hints:
        # - gem5 understands text labels, e.g., "8KiB"
        # - To represent no prefetcher, you can use the value NULL.
        size: str = '32KiB',
        assoc: int = 8,
        tag_latency: int = 1,
        data_latency: int = 3,
        response_latency: int = 1,
        mshrs: int = 16,
        tgts_per_mshr: int = 16,
        write_buffers: int = 8,  # Matched to ChampSim default
        prefetcher: BasePrefetcher = NULL,
        replacement_policy: BaseReplacementPolicy = LRURP(),
        # The below should be false if downstream cache is mostly inclusive or if there is no
        # downstream cache, true if downstream cache is mostly exclusive
        writeback_clean: bool = False,
        # The below is clusivity with respect to the upstream cache. Mostly inclusive means blocks
        # are allocated on all fills; mostly exclusive means allocate only from non-caching sources.
        # L1s should be mostly inclusive. Non-coherent caches, e.g., unified LLCs would generally
        # be mostly exclusive.
        clusivity: Clusivity = "mostly_incl",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.size = size
        self.assoc = assoc
        self.tag_latency = tag_latency
        self.data_latency = data_latency
        self.response_latency = response_latency
        self.mshrs = mshrs
        self.demand_mshr_reserve = self.mshrs / 2
        self.tgts_per_mshr = tgts_per_mshr
        self.write_buffers = write_buffers
        self.prefetcher = prefetcher
        self.replacement_policy = replacement_policy
        self.writeback_clean = writeback_clean
        self.clusivity = clusivity
        print(
            f"Creating L1DCache object: size={self.size}, assoc={self.assoc}, "
            f"pref={type(self.prefetcher)}, repl={type(self.replacement_policy)}"
        )


"""
L1 instruction cache
"""


class L1ICache(Cache):
    def __init__(
        self,
        # FIXME TODO: Set these appropriately.
        size: str = '32KiB',
        assoc: int =  8,
        tag_latency: int =  1,
        data_latency: int = 3,
        response_latency: int = 1,
        mshrs: int = 8,
        tgts_per_mshr: int = 16,
        write_buffers: int = 8,
        prefetcher: BasePrefetcher = NULL,
        replacement_policy: BaseReplacementPolicy = LRURP(),
        # The below should be false if downstream cache is mostly inclusive or if there is no
        # downstream cache, true if downstream cache is mostly exclusive
        writeback_clean: bool = False,
        # The below is clusivity with respect to the upstream cache. Mostly inclusive means blocks
        # are allocated on all fills; mostly exclusive means allocate only from non-caching sources.
        # L1s should be mostly inclusive. Non-coherent caches, e.g., unified LLCs would generally
        # be mostly exclusive.
        clusivity: Clusivity = "mostly_incl",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.size = size
        self.assoc = assoc
        self.tag_latency = tag_latency
        self.data_latency = data_latency
        self.response_latency = response_latency
        self.mshrs = mshrs
        self.demand_mshr_reserve = self.mshrs / 2
        self.tgts_per_mshr = tgts_per_mshr
        self.write_buffers = write_buffers
        self.prefetcher = prefetcher
        self.replacement_policy = replacement_policy
        self.writeback_clean = writeback_clean
        self.clusivity = clusivity
        print(
            f"Creating L1ICache object: size={self.size}, assoc={self.assoc}, "
            f"pref={type(self.prefetcher)}, repl={type(self.replacement_policy)}"
        )


"""
L2 cache
"""


class L2Cache(Cache):
    def __init__(
        self,
        # FIXME TODO: Set these appropriately.
        size: str = '256KiB',
        assoc: int = 4,
        tag_latency: int = 4,
        data_latency: int = 10,
        response_latency: int = 1,
        mshrs: int = 32,
        tgts_per_mshr: int = 16,
        write_buffers: int = 32,  # Matched to ChampSim default
        prefetcher: BasePrefetcher = NULL,
        replacement_policy: BaseReplacementPolicy = LRURP(),
        # The below should be false if downstream cache is mostly inclusive or if there is no
        # downstream cache, true if downstream cache is mostly exclusive
        writeback_clean: bool = False,
        # The below is clusivity with respect to the upstream cache. Mostly inclusive means blocks
        # are allocated on all fills; mostly exclusive means allocate only from non-caching sources.
        # L1s should be mostly inclusive. Non-coherent caches, e.g., unified LLCs would generally
        # be mostly exclusive.
        clusivity: Clusivity = "mostly_incl",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.size = size
        self.assoc = assoc
        self.tag_latency = tag_latency
        self.data_latency = data_latency
        self.response_latency = response_latency
        self.mshrs = mshrs
        self.demand_mshr_reserve = self.mshrs / 2
        self.tgts_per_mshr = tgts_per_mshr
        self.write_buffers = write_buffers
        self.prefetcher = prefetcher
        self.replacement_policy = replacement_policy
        self.writeback_clean = writeback_clean
        self.clusivity = clusivity
        print(
            f"Creating L2Cache object: size={self.size}, assoc={self.assoc}, "
            f"pref={type(self.prefetcher)}, repl={type(self.replacement_policy)}"
        )


"""
Last-level (L3) cache
"""


class LLCache(Cache):
    def __init__(
        self,
        # FIXME TODO: Set these appropriately.
        size: str = '2MiB',
        assoc: int = 16,
        tag_latency: int = 8,
        data_latency: int = 36,
        response_latency: int = 1,
        mshrs: int = 64,
        tgts_per_mshr: int = 32,
        write_buffers: int = 32,  # Matched to ChampSim default
        # FIXME TODO: Set these appropriately.
        prefetcher: BasePrefetcher = StridePrefetcher(degree=3),
        replacement_policy: BaseReplacementPolicy = LRURP(), #  TODO: INSERT YOUR POLICY HERE
        # The below should be false if downstream cache is mostly inclusive or if there is no
        # downstream cache, true if downstream cache is mostly exclusive
        writeback_clean: bool = False,
        # The below is clusivity with respect to the upstream cache. Mostly inclusive means blocks
        # are allocated on all fills; mostly exclusive means allocate only from non-caching sources.
        # L1s should be mostly inclusive.
        clusivity: Clusivity = "mostly_incl",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.size = size
        self.assoc = assoc
        self.tag_latency = tag_latency
        self.data_latency = data_latency
        self.response_latency = response_latency
        self.mshrs = mshrs
        self.demand_mshr_reserve = self.mshrs / 2
        self.tgts_per_mshr = tgts_per_mshr
        self.write_buffers = write_buffers
        self.prefetcher = prefetcher
        self.replacement_policy = replacement_policy()
        self.writeback_clean = writeback_clean
        self.clusivity = clusivity
        print(
            f"Creating LLCache object: size={self.size}, assoc={self.assoc}, "
            f"pref={type(self.prefetcher)}, repl={type(self.replacement_policy)}"
        )


"""
Page table entry cache
(the X86 MMU doesn't support two-level TLBs, but this at least mimics one)
"""


class MMUCache(Cache):
    def __init__(
        self,
        size: str = "8KiB",
        assoc: int = 8,
        tag_latency: int = 1,
        data_latency: int = 1,
        response_latency: int = 1,
        mshrs: int = 8,
        tgts_per_mshr: int = 8,
        writeback_clean: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.size = size
        self.assoc = assoc
        self.tag_latency = tag_latency
        self.data_latency = data_latency
        self.response_latency = response_latency
        self.mshrs = mshrs
        self.tgts_per_mshr = tgts_per_mshr
        self.writeback_clean = writeback_clean
        print("Creating MMUCache object")
