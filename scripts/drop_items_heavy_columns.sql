BEGIN;

LOCK TABLE public.items IN ACCESS EXCLUSIVE MODE;

ALTER TABLE public.items
  DROP COLUMN IF EXISTS author,
  DROP COLUMN IF EXISTS fullname,
  DROP COLUMN IF EXISTS display_author,
  DROP COLUMN IF EXISTS display_handle,
  DROP COLUMN IF EXISTS author_profile_url,
  DROP COLUMN IF EXISTS author_profile_platform,
  DROP COLUMN IF EXISTS title,
  DROP COLUMN IF EXISTS content,
  DROP COLUMN IF EXISTS link,
  DROP COLUMN IF EXISTS x_url,
  DROP COLUMN IF EXISTS images,
  DROP COLUMN IF EXISTS raw_content,
  DROP COLUMN IF EXISTS translated_content;

COMMIT;
