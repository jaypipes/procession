
-- +goose Up
-- SQL in section 'Up' is executed when this migration is applied

CREATE TABLE IF NOT EXISTS organizations (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY
, uuid CHAR(32) CHARACTER SET latin1 COLLATE latin1_bin NOT NULL
, display_name VARCHAR(100) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL
, slug VARCHAR(80) CHARACTER SET latin1 COLLATE latin1_bin NOT NULL
, generation INT NOT NULL
, root_organization_id INT NULL
, parent_organization_id INT NULL
, nested_set_left INT NOT NULL
, nested_set_right INT NOT NULL
, INDEX ix_display_name (display_name(50))
, UNIQUE INDEX uix_slug (slug)
, UNIQUE INDEX uix_uuid (uuid)
, INDEX ix_root_nested_set (root_organization_id, nested_set_left, nested_set_right)
, INDEX ix_root_parent (root_organization_id, parent_organization_id)
);

-- +goose Down
-- SQL section 'Down' is executed when this migration is rolled back
