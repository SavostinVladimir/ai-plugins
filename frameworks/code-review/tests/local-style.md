# Local style consistency

The coordinator runs each variant separately in a fresh context with the
code-style prompt. Supply only the rules and the corresponding contract below,
without expectations.json or the expected outcome. This is a standalone fixture;
the neighbouring inventory fixture README does not apply.

## Project rules

Prefer snake_case for new independent proto contracts. Do not rename existing
public fields. When extending an existing API, preserve the prevailing style
of neighbouring messages.

## Existing contracts.proto

```proto
syntax = "proto3";
package fixture;

message GenerateUploadFileLinkRequest {
  int64 customerID = 1;
  string fileName = 2;
}
message GenerateUploadFileLinkResponse {
  string fileID = 1;
}
message GetFileRequest {
  int64 customerID = 1;
  string fileID = 2;
}
```

## Addition A

```proto
// Метаданные ранее загруженного файла.
message RegisterUploadedFileRequest {
  int64 customer_id = 1;
  string file_name = 2;
}
```

## Addition B

```proto
// Метаданные ранее загруженного файла.
message RegisterUploadedFileRequest {
  int64 customerID = 1;
  string fileName = 2;
}
```

## Variant C: ambiguous existing examples

In a separate run, omit the naming recommendation from the rules. Replace
the existing contracts.proto with the two messages below and supply addition B.

```proto
syntax = "proto3";
package fixture;

message ExistingA {
  int64 customerID = 1;
}
message ExistingB {
  int64 customer_id = 1;
}
```
