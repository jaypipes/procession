-- +goose Up
-- SQL in section 'Up' is executed when this migration is applied

CREATE TABLE IF NOT EXISTS roles (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY
, uuid CHAR(32) CHARACTER SET latin1 COLLATE latin1_bin NOT NULL
, root_organization_id INT UNSIGNED NULL
, display_name VARCHAR(100) CHARACTER SET utf8 COLLATE utf8_unicode_ci NOT NULL
, slug VARCHAR(80) CHARACTER SET latin1 COLLATE latin1_bin NOT NULL
, generation INT NOT NULL
, UNIQUE INDEX uix_uuid (uuid)
, UNIQUE INDEX uix_root_organization_id_display_name (root_organization_id, display_name)
, UNIQUE INDEX uix_slug_root_organization_id (slug, root_organization_id)
);

CREATE TABLE IF NOT EXISTS role_permissions (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY
, role_id INT UNSIGNED NOT NULL
, permission INT UNSIGNED NOT NULL
, UNIQUE INDEX uix_role_id_permission (role_id, permission)
);

CREATE TABLE IF NOT EXISTS user_roles (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY
, user_id INT UNSIGNED NOT NULL
, role_id INT UNSIGNED NOT NULL
, UNIQUE INDEX uix_user_id_role_id (user_id, role_id)
);

-- +goose Down
-- SQL section 'Down' is executed when this migration is rolled back
