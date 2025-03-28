// src/components/scheduler/SchedulePreview.js
import React from "react";
import { Box, VStack, Text, Badge, Card, CardHeader, CardBody, Heading } from "@chakra-ui/react";

const SchedulePreview = ({ scheduleType, description, occurrences, timezone, enabled }) => {
  return (
    <Card>
      <CardHeader>
        <Heading size="sm">Schedule Preview</Heading>
      </CardHeader>
      <CardBody>
        <VStack align="start" spacing={4}>
          <Box>
            <Text fontWeight="bold">Type:</Text>
            <Text>{scheduleType} ({description})</Text>
          </Box>
          
          <Box>
            <Text fontWeight="bold">Status:</Text>
            <Badge colorScheme={enabled ? "green" : "red"}>
              {enabled ? "Enabled" : "Disabled"}
            </Badge>
          </Box>
          
          <Box width="100%">
            <Text fontWeight="bold" mb={2}>Next Occurrences:</Text>
            {occurrences && occurrences.length > 0 ? (
              <VStack align="start">
                {occurrences.map((date, index) => (
                  <Text key={index}>
                    {date.toLocaleString(undefined, {
                      weekday: "short",
                      month: "short",
                      day: "numeric",
                      hour: "numeric",
                      minute: "2-digit",
                      timeZoneName: "short"
                    })}
                  </Text>
                ))}
              </VStack>
            ) : (
              <Text color="gray.500">No upcoming occurrences</Text>
            )}
          </Box>
        </VStack>
      </CardBody>
    </Card>
  );
};

export default SchedulePreview;