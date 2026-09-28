"""Keyless smoke test of altk-evolve's middleware surface (filesystem backend)."""
import os, sys
os.environ["EVOLVE_BACKEND"] = "filesystem"
from altk_evolve.config.evolve import EvolveConfig
from altk_evolve.frontend.client.evolve_client import EvolveClient
from altk_evolve.schema.core import Entity

results = []
def check(name, cond):
    results.append((name, bool(cond))); print(("PASS" if cond else "FAIL"), name)

cfg = EvolveConfig(backend="filesystem")
if hasattr(cfg, "filesystem"): cfg.filesystem.data_dir = "smoke_data"
c = EvolveClient(cfg)
check("backend ready", c.ready())
ns = "ae_smoke"
if c.namespace_exists(ns):
    c.delete_namespace(ns)  # start clean so repeated runs give the same result
c.ensure_namespace(ns)
check("namespace created", c.namespace_exists(ns))

ups = c.update_entities(ns, [Entity(type="guideline", content="Use the album_id field, not the album title, when calling the playlist API.",
           metadata={"trigger": "calling playlist API", "owner_id": "alice", "visibility": "private", "creation_mode": "manual"})],
    enable_conflict_resolution=False)
ups += c.update_entities(ns, [Entity(type="fact", content="User prefers Java 11 for all builds.",
           metadata={"owner_id": "alice", "visibility": "private"})], enable_conflict_resolution=False)
check("typed entities written (guideline + fact)", len(ups) == 2)

all_e = c.get_all_entities(ns)
g = [e for e in all_e if e.type == "guideline"]; f = [e for e in all_e if e.type == "fact"]
check("types kept distinct", len(g) == 1 and len(f) == 1)

hits = c.search_entities(ns, query="playlist API", filters={"type": "guideline"})
check("type-filtered retrieval returns the guideline", any("album_id" in str(e.content) for e in hits))

gid = g[0].id
c.patch_entity_metadata(ns, gid, {"visibility": "public"})
pub = c.get_public_entities()
check("publish -> visible cross-namespace", any(e.id == gid for e in pub))
c.patch_entity_metadata(ns, gid, {"visibility": "private"})
check("unpublish -> no longer public", not any(e.id == gid for e in c.get_public_entities()))

check("provenance metadata retained", c.get_entity_by_id(ns, gid).metadata.get("creation_mode") == "manual")
c.delete_entity_by_id(ns, f[0].id)
check("delete removes entity", c.get_entity_by_id(ns, f[0].id) is None)

ok = sum(p for _, p in results); print(f"\n{ok}/{len(results)} checks passed")
sys.exit(0 if ok == len(results) else 1)
