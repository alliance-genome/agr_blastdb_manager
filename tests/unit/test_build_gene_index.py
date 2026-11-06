"""
The gene index extractor, which turns the Alliance all_genes GFFs into the
per-assembly tables agr_sequenceserver reads.

What matters here is the curie filter. Three of the nine species carry gene
rows whose curie the Alliance orthologue API cannot answer, and the API returns
HTTP 200 with total=0 for them, so the status code is not a usable signal. If a
placeholder reaches the app it shows an orthologue expander that can only ever
come back empty, which is worse than showing none.
"""

import gzip
import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import build_gene_index as bgi


def gff(lines):
    return io.BytesIO("\n".join(lines).encode())


ROW = "{ref}\tSGD\t{kind}\t{start}\t{end}\t.\t+\t.\t{attrs}"


class TestParseGenes:
    def test_reads_a_gene_row(self):
        rows = list(bgi.parse_genes(gff([
            ROW.format(ref="chrI", kind="gene", start=335, end=649,
                       attrs="ID=YAL069W;Name=YAL069W;curie=SGD:S000002143"),
        ])))
        assert rows == [("chrI", 335, 649, "YAL069W", "SGD:S000002143", None)]

    def test_skips_everything_that_is_not_a_gene(self):
        """A GFF is mostly exons and CDS: measured on the yeast file, 6,613
        gene rows out of 33,867 lines."""
        rows = list(bgi.parse_genes(gff([
            "##gff-version 3",
            ROW.format(ref="chrI", kind="mRNA", start=1, end=99, attrs="ID=m1;curie=SGD:X"),
            ROW.format(ref="chrI", kind="CDS", start=1, end=99, attrs="ID=c1"),
            ROW.format(ref="chrI", kind="exon", start=1, end=99, attrs="ID=e1"),
            ROW.format(ref="chrI", kind="gene", start=1, end=99,
                       attrs="Name=g1;curie=SGD:S000000001"),
        ])))
        assert [r[3] for r in rows] == ["g1"]

    def test_keeps_a_gene_with_no_name(self):
        rows = list(bgi.parse_genes(gff([
            ROW.format(ref="chrII", kind="gene", start=10, end=20, attrs="ID=only-an-id"),
        ])))
        assert rows[0][3] is None
        assert rows[0][4] is None
        assert rows[0][5] is None

    def test_ignores_a_short_or_malformed_line(self):
        rows = list(bgi.parse_genes(gff(["chrI\tSGD\tgene", "", "#comment"])))
        assert rows == []


class TestCurieFilter:
    @pytest.mark.parametrize("curie", [
        "HGNC:144", "MGI:87905", "RGD:628837", "ZFIN:ZDB-GENE-990415-8",
        "FB:FBgn0267594", "WB:WBGene00023193", "SGD:S000002143",
        "Xenbase:XB-GENE-29086023",
    ])
    def test_keeps_a_curie_the_orthologue_api_answers(self, curie):
        rows = list(bgi.parse_genes(gff([
            ROW.format(ref="chr1", kind="gene", start=1, end=2,
                       attrs=f"Name=g;curie={curie}"),
        ])))
        assert rows[0][4] == curie

    def test_drops_modelID(self):
        """Xenopus laevis uses modelID: on 15,760 of its 42,645 gene rows where
        no Xenbase gene exists. modelID:XBXL10_1g1 returns 200 with total=0."""
        rows = list(bgi.parse_genes(gff([
            ROW.format(ref="chr1L", kind="gene", start=1, end=2,
                       attrs="Name=LOC108704873;curie=modelID:XBXL10_1g1"),
        ])))
        assert rows[0][3] == "LOC108704873"
        assert rows[0][4] is None, "a placeholder must not reach the app as a curie"
        # Kept as the dropped value, so build() can count placeholders rather
        # than report a flat zero.
        assert rows[0][5] == "modelID:XBXL10_1g1"

    def test_drops_a_refseq_curie(self):
        """The X. laevis GFF carries 80,896 RefSeq: curies, on rows other than
        gene. Dropped rather than passed through: the orthologue API is keyed on
        MOD curies."""
        rows = list(bgi.parse_genes(gff([
            ROW.format(ref="chr1L", kind="gene", start=1, end=2,
                       attrs="Name=g;curie=RefSeq:XM_018121069.2"),
        ])))
        assert rows[0][4] is None

    def test_keeps_the_name_when_there_is_no_curie_at_all(self):
        """Danio rerio carries a curie on 22,542 of 49,257 gene rows, 45.8%, so
        this is the ordinary case for that species."""
        rows = list(bgi.parse_genes(gff([
            ROW.format(ref="4", kind="gene", start=1, end=2, attrs="Name=LOC141383674"),
        ])))
        assert rows[0][3] == "LOC141383674"
        assert rows[0][4] is None


class TestAllGenesTracks:
    def test_finds_only_all_genes_tracks(self):
        config = {"tracks": [
            {"trackId": "Homo_sapiens_all_genes",
             "adapter": {"gffGzLocation": {"uri": "s3://human.gff.gz"}}},
            {"trackId": "Homo_sapiens_variants",
             "adapter": {"gffGzLocation": {"uri": "s3://variants.gff.gz"}}},
            # No location, so nothing to extract from.
            {"trackId": "Mus_musculus_all_genes", "adapter": {}},
        ]}
        assert bgi.all_genes_tracks(config) == {"Homo_sapiens": "s3://human.gff.gz"}

    def test_answers_empty_for_a_config_with_no_tracks(self):
        assert bgi.all_genes_tracks({}) == {}


class TestBuild:
    def test_writes_a_sorted_index_the_app_can_read(self, tmp_path, monkeypatch):
        # Deliberately out of order by start, to prove the sort runs. The
        # sources are named .sorted and were in fact sorted when measured, but
        # a table that is not sorted by start cannot be binary-searched, and
        # the app's lookup assumes it is.
        body = gzip.compress("\n".join([
            ROW.format(ref="chrI", kind="gene", start=500, end=600,
                       attrs="Name=later;curie=SGD:S2"),
            ROW.format(ref="chrI", kind="gene", start=100, end=200,
                       attrs="Name=earlier;curie=SGD:S1"),
            ROW.format(ref="chrI", kind="exon", start=1, end=9, attrs="ID=e"),
        ]).encode())
        monkeypatch.setattr(bgi, "fetch", lambda url, timeout=600: body)

        path, counts, n_refs, unsorted = bgi.build(
            "Test_organism", "s3://test.gff.gz", "9.2.0", tmp_path
        )

        assert path.name == "Test_organism.genes.json.gz"
        assert counts == {"genes": 2, "with_curie": 2, "unusable_curie": 0, "no_name": 0}
        assert n_refs == 1
        assert unsorted == ["chrI"]

        with gzip.open(path, "rt") as handle:
            doc = json.load(handle)
        assert doc["assembly"] == "Test_organism"
        assert doc["release"] == "9.2.0"
        assert doc["source"] == "s3://test.gff.gz"
        # Sorted by start, and shaped [start, end, name, curie] as
        # lib/sequenceserver/gene_index.rb reads it.
        assert doc["refs"]["chrI"] == [
            [100, 200, "earlier", "SGD:S1"],
            [500, 600, "later", "SGD:S2"],
        ]

    def test_counts_a_dropped_placeholder_curie(self, tmp_path, monkeypatch):
        """unusable_curie was initialised and never incremented, so it
        reported 0 for the 15,760 modelID: rows in X. laevis."""
        body = gzip.compress("\n".join([
            ROW.format(ref="chr1L", kind="gene", start=1, end=2,
                       attrs="Name=a;curie=modelID:XBXL10_1g1"),
            ROW.format(ref="chr1L", kind="gene", start=5, end=6,
                       attrs="Name=b;curie=Xenbase:XB-GENE-1"),
            ROW.format(ref="chr1L", kind="gene", start=9, end=10, attrs="Name=c"),
        ]).encode())
        monkeypatch.setattr(bgi, "fetch", lambda url, timeout=600: body)
        _, counts, _, _ = bgi.build("T", "s3://t.gz", "9.2.0", tmp_path)
        assert counts["genes"] == 3
        assert counts["with_curie"] == 1
        assert counts["unusable_curie"] == 1, "a dropped placeholder must be counted"

    def test_counts_a_missing_name(self, tmp_path, monkeypatch):
        body = gzip.compress(
            ROW.format(ref="chrI", kind="gene", start=1, end=2, attrs="ID=x").encode()
        )
        monkeypatch.setattr(bgi, "fetch", lambda url, timeout=600: body)
        _, counts, _, _ = bgi.build("T", "s3://t.gz", "9.2.0", tmp_path)
        assert counts["no_name"] == 1
        assert counts["with_curie"] == 0
