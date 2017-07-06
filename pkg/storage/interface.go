package storage

// Generic interface for anything that behaves similiar to a database/sql
// Rows struct. Useful for test mocking and abstracting a storage layer.
type RowIterator interface {
    Next() bool
    Close() error
    Scan(dest ...interface{}) error
}
