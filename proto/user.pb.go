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
	DisplayName string `protobuf:"bytes,2,opt,name=display_name,json=displayName" json:"display_name,omitempty"`
	Email       string `protobuf:"bytes,3,opt,name=email" json:"email,omitempty"`
	Generation  uint32 `protobuf:"varint,100,opt,name=generation" json:"generation,omitempty"`
}

func (m *User) Reset()                    { *m = User{} }
func (m *User) String() string            { return proto.CompactTextString(m) }
func (*User) ProtoMessage()               {}
func (*User) Descriptor() ([]byte, []int) { return fileDescriptor8, []int{0} }

func (m *User) GetUuid() string {
	if m != nil {
		return m.Uuid
	}
	return ""
}

func (m *User) GetDisplayName() string {
	if m != nil {
		return m.DisplayName
	}
	return ""
}

func (m *User) GetEmail() string {
	if m != nil {
		return m.Email
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
	Session  *Session `protobuf:"bytes,1,opt,name=session" json:"session,omitempty"`
	UserUuid string   `protobuf:"bytes,2,opt,name=user_uuid,json=userUuid" json:"user_uuid,omitempty"`
}

func (m *GetUserRequest) Reset()                    { *m = GetUserRequest{} }
func (m *GetUserRequest) String() string            { return proto.CompactTextString(m) }
func (*GetUserRequest) ProtoMessage()               {}
func (*GetUserRequest) Descriptor() ([]byte, []int) { return fileDescriptor8, []int{1} }

func (m *GetUserRequest) GetSession() *Session {
	if m != nil {
		return m.Session
	}
	return nil
}

func (m *GetUserRequest) GetUserUuid() string {
	if m != nil {
		return m.UserUuid
	}
	return ""
}

type SetUserRequest struct {
	Session *Session                `protobuf:"bytes,1,opt,name=session" json:"session,omitempty"`
	User    *SetUserRequest_SetUser `protobuf:"bytes,2,opt,name=user" json:"user,omitempty"`
}

func (m *SetUserRequest) Reset()                    { *m = SetUserRequest{} }
func (m *SetUserRequest) String() string            { return proto.CompactTextString(m) }
func (*SetUserRequest) ProtoMessage()               {}
func (*SetUserRequest) Descriptor() ([]byte, []int) { return fileDescriptor8, []int{2} }

func (m *SetUserRequest) GetSession() *Session {
	if m != nil {
		return m.Session
	}
	return nil
}

func (m *SetUserRequest) GetUser() *SetUserRequest_SetUser {
	if m != nil {
		return m.User
	}
	return nil
}

type SetUserRequest_SetUser struct {
	Uuid        string       `protobuf:"bytes,1,opt,name=uuid" json:"uuid,omitempty"`
	DisplayName *StringValue `protobuf:"bytes,2,opt,name=display_name,json=displayName" json:"display_name,omitempty"`
	Email       *StringValue `protobuf:"bytes,3,opt,name=email" json:"email,omitempty"`
}

func (m *SetUserRequest_SetUser) Reset()                    { *m = SetUserRequest_SetUser{} }
func (m *SetUserRequest_SetUser) String() string            { return proto.CompactTextString(m) }
func (*SetUserRequest_SetUser) ProtoMessage()               {}
func (*SetUserRequest_SetUser) Descriptor() ([]byte, []int) { return fileDescriptor8, []int{2, 0} }

func (m *SetUserRequest_SetUser) GetUuid() string {
	if m != nil {
		return m.Uuid
	}
	return ""
}

func (m *SetUserRequest_SetUser) GetDisplayName() *StringValue {
	if m != nil {
		return m.DisplayName
	}
	return nil
}

func (m *SetUserRequest_SetUser) GetEmail() *StringValue {
	if m != nil {
		return m.Email
	}
	return nil
}

type SearchUsersFilters struct {
	Uuids     []string `protobuf:"bytes,1,rep,name=uuids" json:"uuids,omitempty"`
	NamesLike []string `protobuf:"bytes,2,rep,name=names_like,json=namesLike" json:"names_like,omitempty"`
	Emails    []string `protobuf:"bytes,3,rep,name=emails" json:"emails,omitempty"`
}

func (m *SearchUsersFilters) Reset()                    { *m = SearchUsersFilters{} }
func (m *SearchUsersFilters) String() string            { return proto.CompactTextString(m) }
func (*SearchUsersFilters) ProtoMessage()               {}
func (*SearchUsersFilters) Descriptor() ([]byte, []int) { return fileDescriptor8, []int{3} }

func (m *SearchUsersFilters) GetUuids() []string {
	if m != nil {
		return m.Uuids
	}
	return nil
}

func (m *SearchUsersFilters) GetNamesLike() []string {
	if m != nil {
		return m.NamesLike
	}
	return nil
}

func (m *SearchUsersFilters) GetEmails() []string {
	if m != nil {
		return m.Emails
	}
	return nil
}

type SearchUsersRequest struct {
	Filters *SearchUsersFilters `protobuf:"bytes,1,opt,name=filters" json:"filters,omitempty"`
	Options *SearchOptions      `protobuf:"bytes,2,opt,name=options" json:"options,omitempty"`
}

func (m *SearchUsersRequest) Reset()                    { *m = SearchUsersRequest{} }
func (m *SearchUsersRequest) String() string            { return proto.CompactTextString(m) }
func (*SearchUsersRequest) ProtoMessage()               {}
func (*SearchUsersRequest) Descriptor() ([]byte, []int) { return fileDescriptor8, []int{4} }

func (m *SearchUsersRequest) GetFilters() *SearchUsersFilters {
	if m != nil {
		return m.Filters
	}
	return nil
}

func (m *SearchUsersRequest) GetOptions() *SearchOptions {
	if m != nil {
		return m.Options
	}
	return nil
}

func init() {
	proto.RegisterType((*User)(nil), "procession.User")
	proto.RegisterType((*GetUserRequest)(nil), "procession.GetUserRequest")
	proto.RegisterType((*SetUserRequest)(nil), "procession.SetUserRequest")
	proto.RegisterType((*SetUserRequest_SetUser)(nil), "procession.SetUserRequest.SetUser")
	proto.RegisterType((*SearchUsersFilters)(nil), "procession.SearchUsersFilters")
	proto.RegisterType((*SearchUsersRequest)(nil), "procession.SearchUsersRequest")
}

func init() { proto.RegisterFile("user.proto", fileDescriptor8) }

var fileDescriptor8 = []byte{
	// 379 bytes of a gzipped FileDescriptorProto
	0x1f, 0x8b, 0x08, 0x00, 0x00, 0x09, 0x6e, 0x88, 0x02, 0xff, 0xa4, 0x52, 0x4d, 0x4f, 0xea, 0x40,
	0x14, 0x4d, 0x81, 0x47, 0x1f, 0xb7, 0xc0, 0x62, 0xde, 0x8b, 0x56, 0x8c, 0x04, 0xbb, 0x62, 0x03,
	0x0b, 0x48, 0x8c, 0xf1, 0x07, 0xe8, 0xc6, 0x68, 0x52, 0x82, 0x2b, 0x13, 0x32, 0xd2, 0x2b, 0x4e,
	0x28, 0x6d, 0x9d, 0xdb, 0xc6, 0xb8, 0xd5, 0x8d, 0x3f, 0xdb, 0xcc, 0x47, 0x95, 0x2a, 0x71, 0xe3,
	0xaa, 0x3d, 0xe7, 0x9e, 0x39, 0x73, 0xe6, 0xcc, 0x00, 0x14, 0x84, 0x72, 0x9c, 0xc9, 0x34, 0x4f,
	0x19, 0x64, 0x32, 0x5d, 0x22, 0x91, 0x48, 0x93, 0x5e, 0x9b, 0x90, 0xcb, 0xe5, 0x83, 0x99, 0xf4,
	0x3a, 0x64, 0x68, 0x0b, 0xbb, 0x4f, 0x92, 0x67, 0x19, 0x4a, 0x32, 0x38, 0x20, 0x68, 0xcc, 0x09,
	0x25, 0x63, 0xd0, 0x28, 0x0a, 0x11, 0xf9, 0xce, 0xc0, 0x19, 0xb6, 0x42, 0xfd, 0xcf, 0x8e, 0xa1,
	0x1d, 0x09, 0xca, 0x62, 0xfe, 0xbc, 0x48, 0xf8, 0x06, 0xfd, 0x9a, 0x9e, 0x79, 0x96, 0xbb, 0xe2,
	0x1b, 0x64, 0xff, 0xe1, 0x0f, 0x6e, 0xb8, 0x88, 0xfd, 0xba, 0x9e, 0x19, 0xc0, 0xfa, 0x00, 0x2b,
	0x4c, 0x50, 0xf2, 0x5c, 0xa4, 0x89, 0x1f, 0x0d, 0x9c, 0x61, 0x27, 0xdc, 0x62, 0x82, 0x5b, 0xe8,
	0x5e, 0x60, 0xae, 0xf6, 0x0d, 0xf1, 0xb1, 0x40, 0xca, 0xd9, 0x08, 0x5c, 0x9b, 0x53, 0x27, 0xf0,
	0x26, 0xff, 0xc6, 0x9f, 0x27, 0x1a, 0xcf, 0xcc, 0x37, 0x2c, 0x35, 0xec, 0x10, 0x5a, 0xea, 0xf0,
	0x0b, 0x1d, 0xd9, 0xc4, 0xfa, 0xab, 0x88, 0x79, 0x21, 0xa2, 0xe0, 0xa5, 0x06, 0xdd, 0xd9, 0xaf,
	0xec, 0x4f, 0xa0, 0xa1, 0xdc, 0xb4, 0xb3, 0x37, 0x09, 0xaa, 0xda, 0x6d, 0xe3, 0x0f, 0xa8, 0xf5,
	0xbd, 0x37, 0x07, 0x5c, 0xcb, 0xec, 0x2c, 0xf4, 0x6c, 0x47, 0xa1, 0xde, 0x64, 0xbf, 0xe2, 0x9f,
	0x4b, 0x91, 0xac, 0x6e, 0x78, 0x5c, 0x60, 0xb5, 0xe9, 0xd1, 0x76, 0xd3, 0x3f, 0x2c, 0x32, 0xaa,
	0x80, 0x03, 0x9b, 0xe9, 0x67, 0xa0, 0xc2, 0xd0, 0xb9, 0x88, 0x73, 0x94, 0xa4, 0xae, 0x4b, 0x05,
	0x21, 0xdf, 0x19, 0xd4, 0xd5, 0x75, 0x69, 0xc0, 0x8e, 0x00, 0x54, 0x1c, 0x5a, 0xc4, 0x62, 0xad,
	0x42, 0xa9, 0x51, 0x4b, 0x33, 0x97, 0x62, 0x8d, 0x6c, 0x0f, 0x9a, 0xda, 0x93, 0xfc, 0xba, 0x1e,
	0x59, 0x14, 0xbc, 0x3a, 0x95, 0x3d, 0xca, 0xae, 0x4f, 0xc1, 0xbd, 0x37, 0xdb, 0xd9, 0xae, 0xfb,
	0xd5, 0xfe, 0xbe, 0x86, 0x0a, 0x4b, 0x39, 0x9b, 0x82, 0x9b, 0x66, 0xea, 0x81, 0x90, 0x6d, 0xe6,
	0xe0, 0xfb, 0xca, 0x6b, 0x23, 0x08, 0x4b, 0xe5, 0x5d, 0x53, 0xbf, 0xe3, 0xe9, 0x7b, 0x00, 0x00,
	0x00, 0xff, 0xff, 0xbb, 0xc4, 0x60, 0x38, 0x0e, 0x03, 0x00, 0x00,
}
