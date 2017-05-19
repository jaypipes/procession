// Code generated by protoc-gen-go.
// source: user.proto
// DO NOT EDIT!

package procession

import proto "github.com/golang/protobuf/proto"
import fmt "fmt"
import math "math"

// Reference imports to suppress errors if they are not otherwise used.
var _ = proto.Marshal
var _ = fmt.Errorf
var _ = math.Inf

// Basic information about a user of the system
type User struct {
	Uuid        string `protobuf:"bytes,1,opt,name=uuid" json:"uuid,omitempty"`
	Email       string `protobuf:"bytes,2,opt,name=email" json:"email,omitempty"`
	DisplayName string `protobuf:"bytes,3,opt,name=display_name,json=displayName" json:"display_name,omitempty"`
	Slug        string `protobuf:"bytes,4,opt,name=slug" json:"slug,omitempty"`
	Generation  uint32 `protobuf:"varint,100,opt,name=generation" json:"generation,omitempty"`
}

func (m *User) Reset()                    { *m = User{} }
func (m *User) String() string            { return proto.CompactTextString(m) }
func (*User) ProtoMessage()               {}
func (*User) Descriptor() ([]byte, []int) { return fileDescriptor5, []int{0} }

func (m *User) GetUuid() string {
	if m != nil {
		return m.Uuid
	}
	return ""
}

func (m *User) GetEmail() string {
	if m != nil {
		return m.Email
	}
	return ""
}

func (m *User) GetDisplayName() string {
	if m != nil {
		return m.DisplayName
	}
	return ""
}

func (m *User) GetSlug() string {
	if m != nil {
		return m.Slug
	}
	return ""
}

func (m *User) GetGeneration() uint32 {
	if m != nil {
		return m.Generation
	}
	return 0
}

type GetUserRequest struct {
	Session *Session `protobuf:"bytes,1,opt,name=session" json:"session,omitempty"`
	Search  string   `protobuf:"bytes,2,opt,name=search" json:"search,omitempty"`
}

func (m *GetUserRequest) Reset()                    { *m = GetUserRequest{} }
func (m *GetUserRequest) String() string            { return proto.CompactTextString(m) }
func (*GetUserRequest) ProtoMessage()               {}
func (*GetUserRequest) Descriptor() ([]byte, []int) { return fileDescriptor5, []int{1} }

func (m *GetUserRequest) GetSession() *Session {
	if m != nil {
		return m.Session
	}
	return nil
}

func (m *GetUserRequest) GetSearch() string {
	if m != nil {
		return m.Search
	}
	return ""
}

type SetUserFields struct {
	Email       *StringValue `protobuf:"bytes,2,opt,name=email" json:"email,omitempty"`
	DisplayName *StringValue `protobuf:"bytes,3,opt,name=display_name,json=displayName" json:"display_name,omitempty"`
}

func (m *SetUserFields) Reset()                    { *m = SetUserFields{} }
func (m *SetUserFields) String() string            { return proto.CompactTextString(m) }
func (*SetUserFields) ProtoMessage()               {}
func (*SetUserFields) Descriptor() ([]byte, []int) { return fileDescriptor5, []int{2} }

func (m *SetUserFields) GetEmail() *StringValue {
	if m != nil {
		return m.Email
	}
	return nil
}

func (m *SetUserFields) GetDisplayName() *StringValue {
	if m != nil {
		return m.DisplayName
	}
	return nil
}

type SetUserRequest struct {
	Session    *Session       `protobuf:"bytes,1,opt,name=session" json:"session,omitempty"`
	Search     *StringValue   `protobuf:"bytes,2,opt,name=search" json:"search,omitempty"`
	UserFields *SetUserFields `protobuf:"bytes,3,opt,name=user_fields,json=userFields" json:"user_fields,omitempty"`
}

func (m *SetUserRequest) Reset()                    { *m = SetUserRequest{} }
func (m *SetUserRequest) String() string            { return proto.CompactTextString(m) }
func (*SetUserRequest) ProtoMessage()               {}
func (*SetUserRequest) Descriptor() ([]byte, []int) { return fileDescriptor5, []int{3} }

func (m *SetUserRequest) GetSession() *Session {
	if m != nil {
		return m.Session
	}
	return nil
}

func (m *SetUserRequest) GetSearch() *StringValue {
	if m != nil {
		return m.Search
	}
	return nil
}

func (m *SetUserRequest) GetUserFields() *SetUserFields {
	if m != nil {
		return m.UserFields
	}
	return nil
}

type SetUserResponse struct {
	User *User `protobuf:"bytes,1,opt,name=user" json:"user,omitempty"`
}

func (m *SetUserResponse) Reset()                    { *m = SetUserResponse{} }
func (m *SetUserResponse) String() string            { return proto.CompactTextString(m) }
func (*SetUserResponse) ProtoMessage()               {}
func (*SetUserResponse) Descriptor() ([]byte, []int) { return fileDescriptor5, []int{4} }

func (m *SetUserResponse) GetUser() *User {
	if m != nil {
		return m.User
	}
	return nil
}

type UserListFilters struct {
	Uuids        []string `protobuf:"bytes,1,rep,name=uuids" json:"uuids,omitempty"`
	DisplayNames []string `protobuf:"bytes,2,rep,name=display_names,json=displayNames" json:"display_names,omitempty"`
	Emails       []string `protobuf:"bytes,3,rep,name=emails" json:"emails,omitempty"`
	Slugs        []string `protobuf:"bytes,4,rep,name=slugs" json:"slugs,omitempty"`
}

func (m *UserListFilters) Reset()                    { *m = UserListFilters{} }
func (m *UserListFilters) String() string            { return proto.CompactTextString(m) }
func (*UserListFilters) ProtoMessage()               {}
func (*UserListFilters) Descriptor() ([]byte, []int) { return fileDescriptor5, []int{5} }

func (m *UserListFilters) GetUuids() []string {
	if m != nil {
		return m.Uuids
	}
	return nil
}

func (m *UserListFilters) GetDisplayNames() []string {
	if m != nil {
		return m.DisplayNames
	}
	return nil
}

func (m *UserListFilters) GetEmails() []string {
	if m != nil {
		return m.Emails
	}
	return nil
}

func (m *UserListFilters) GetSlugs() []string {
	if m != nil {
		return m.Slugs
	}
	return nil
}

type UserListRequest struct {
	Session *Session         `protobuf:"bytes,1,opt,name=session" json:"session,omitempty"`
	Filters *UserListFilters `protobuf:"bytes,2,opt,name=filters" json:"filters,omitempty"`
	Options *SearchOptions   `protobuf:"bytes,3,opt,name=options" json:"options,omitempty"`
}

func (m *UserListRequest) Reset()                    { *m = UserListRequest{} }
func (m *UserListRequest) String() string            { return proto.CompactTextString(m) }
func (*UserListRequest) ProtoMessage()               {}
func (*UserListRequest) Descriptor() ([]byte, []int) { return fileDescriptor5, []int{6} }

func (m *UserListRequest) GetSession() *Session {
	if m != nil {
		return m.Session
	}
	return nil
}

func (m *UserListRequest) GetFilters() *UserListFilters {
	if m != nil {
		return m.Filters
	}
	return nil
}

func (m *UserListRequest) GetOptions() *SearchOptions {
	if m != nil {
		return m.Options
	}
	return nil
}

func init() {
	proto.RegisterType((*User)(nil), "procession.User")
	proto.RegisterType((*GetUserRequest)(nil), "procession.GetUserRequest")
	proto.RegisterType((*SetUserFields)(nil), "procession.SetUserFields")
	proto.RegisterType((*SetUserRequest)(nil), "procession.SetUserRequest")
	proto.RegisterType((*SetUserResponse)(nil), "procession.SetUserResponse")
	proto.RegisterType((*UserListFilters)(nil), "procession.UserListFilters")
	proto.RegisterType((*UserListRequest)(nil), "procession.UserListRequest")
}

func init() { proto.RegisterFile("user.proto", fileDescriptor5) }

var fileDescriptor5 = []byte{
	// 425 bytes of a gzipped FileDescriptorProto
	0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0xff, 0xa4, 0x53, 0xc1, 0x8e, 0xd3, 0x30,
	0x10, 0x55, 0x76, 0xc3, 0x56, 0x4c, 0x9a, 0x2e, 0x32, 0x08, 0xcc, 0x22, 0xa1, 0x12, 0x38, 0xec,
	0x65, 0x8b, 0xd4, 0x0a, 0x21, 0xf5, 0x03, 0xca, 0x05, 0x81, 0x94, 0x0a, 0x38, 0x56, 0xa6, 0x99,
	0x16, 0x4b, 0x69, 0x12, 0x3c, 0x89, 0x10, 0xfd, 0x01, 0x7e, 0x86, 0x8f, 0x44, 0x63, 0x3b, 0xc5,
	0x45, 0xd0, 0x03, 0x7b, 0xaa, 0xdf, 0xcc, 0x74, 0xfc, 0xde, 0xf3, 0x0b, 0x40, 0x47, 0x68, 0x26,
	0x8d, 0xa9, 0xdb, 0x5a, 0x40, 0x63, 0xea, 0x35, 0x12, 0xe9, 0xba, 0xba, 0x1a, 0x12, 0x2a, 0xb3,
	0xfe, 0xe2, 0x3a, 0x57, 0x29, 0xb9, 0xb2, 0x87, 0xa3, 0x6f, 0x46, 0x35, 0x0d, 0x1a, 0x72, 0x38,
	0xfb, 0x11, 0x41, 0xfc, 0x81, 0xd0, 0x08, 0x01, 0x71, 0xd7, 0xe9, 0x42, 0x46, 0xe3, 0xe8, 0xfa,
	0x6e, 0x6e, 0xcf, 0xe2, 0x01, 0xdc, 0xc1, 0x9d, 0xd2, 0xa5, 0x3c, 0xb3, 0x45, 0x07, 0xc4, 0x33,
	0x18, 0x16, 0x9a, 0x9a, 0x52, 0x7d, 0x5f, 0x55, 0x6a, 0x87, 0xf2, 0xdc, 0x36, 0x13, 0x5f, 0x7b,
	0xa7, 0x76, 0xc8, 0xcb, 0xa8, 0xec, 0xb6, 0x32, 0x76, 0xcb, 0xf8, 0x2c, 0x9e, 0x02, 0x6c, 0xb1,
	0x42, 0xa3, 0x5a, 0x5d, 0x57, 0xb2, 0x18, 0x47, 0xd7, 0x69, 0x1e, 0x54, 0xb2, 0x4f, 0x30, 0x7a,
	0x83, 0x2d, 0x73, 0xc9, 0xf1, 0x6b, 0x87, 0xd4, 0x8a, 0x1b, 0x18, 0x78, 0xf2, 0x96, 0x55, 0x32,
	0xbd, 0x3f, 0xf9, 0x2d, 0x73, 0xb2, 0x74, 0xbf, 0x79, 0x3f, 0x23, 0x1e, 0xc2, 0x85, 0x53, 0xee,
	0xe9, 0x7a, 0x94, 0xed, 0x21, 0x5d, 0xba, 0xc5, 0x0b, 0x8d, 0x65, 0x41, 0xe2, 0x26, 0x94, 0x95,
	0x4c, 0x1f, 0x1d, 0x6d, 0x6d, 0x8d, 0xae, 0xb6, 0x1f, 0x55, 0xd9, 0x61, 0xaf, 0x77, 0xfe, 0x17,
	0xbd, 0x27, 0xfe, 0x15, 0x1a, 0x91, 0xfd, 0x8c, 0x60, 0xb4, 0xbc, 0x95, 0xaa, 0x97, 0x47, 0xaa,
	0x4e, 0xdc, 0xeb, 0xc7, 0xc4, 0x1c, 0x12, 0x0e, 0xc6, 0x6a, 0x63, 0xc5, 0x7a, 0xb6, 0x8f, 0x8f,
	0xef, 0x08, 0xdc, 0xc8, 0x6d, 0x8c, 0xdc, 0x39, 0x7b, 0x0d, 0x97, 0x07, 0xb6, 0xd4, 0xd4, 0x15,
	0xa1, 0x78, 0x01, 0x31, 0x0f, 0x78, 0xae, 0xf7, 0xc2, 0x3d, 0x76, 0xce, 0x76, 0xb3, 0x3d, 0x5c,
	0x32, 0x7a, 0xab, 0xa9, 0x5d, 0xe8, 0xb2, 0x45, 0x43, 0x1c, 0x1e, 0x0e, 0x11, 0xc9, 0x68, 0x7c,
	0xce, 0xe1, 0xb1, 0x40, 0x3c, 0x87, 0x34, 0x34, 0x93, 0xe4, 0x99, 0xed, 0x0e, 0x03, 0xd3, 0x88,
	0x5f, 0xd2, 0x5a, 0xcf, 0xec, 0xb9, 0xeb, 0x11, 0xaf, 0xe4, 0x28, 0x91, 0x8c, 0xdd, 0x4a, 0x0b,
	0xd8, 0xe3, 0xc3, 0xe5, 0xff, 0x69, 0xf2, 0x2b, 0x18, 0x6c, 0x1c, 0x6d, 0xef, 0xf2, 0x93, 0x3f,
	0x75, 0x06, 0xca, 0xf2, 0x7e, 0x56, 0xcc, 0x60, 0x50, 0x37, 0x1c, 0xde, 0x7f, 0xd8, 0xcc, 0xef,
	0xf1, 0xde, 0x0d, 0xe4, 0xfd, 0xe4, 0xe7, 0x0b, 0xfb, 0xe1, 0xcd, 0x7e, 0x05, 0x00, 0x00, 0xff,
	0xff, 0xe3, 0x4a, 0xb2, 0x35, 0xbf, 0x03, 0x00, 0x00,
}
