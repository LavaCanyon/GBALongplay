# Building a full album within the 128 MiB workspace limit

A final 64 MiB ROM and four approximately 15.875 MiB GLV2 streams cannot all remain alongside large source uploads. The build therefore uses staged cleanup.

1. Remove superseded 64 MiB test ROMs.
2. Upload and encode one source episode at a time.
3. Verify the resulting GLV2 stream, then remove its large source upload with user permission.
4. Retain only the four encoded GLV2 streams (maximum combined target about 63.5 MiB), code, and small thumbnails.
5. Build the temporary GLA1 album and 64 MiB Matrix ROM in one operation.
6. After validating the ROM, delete the temporary GLA1 and per-episode GLV2 files, retaining the final ROM and source code.

The filesystem may briefly contain more intermediate data during a tool call, but the persisted turn snapshot must remain under 128 MiB. If an individual source upload is too large to coexist with existing encoded streams, the already-verified streams can be temporarily removed and regenerated, or the source can be externally reduced before upload.

Never remove a user-uploaded source episode without explicit permission after its encoded stream has been verified.
